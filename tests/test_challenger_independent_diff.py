"""
tests/test_challenger_independent_diff.py

Independent Empirical Verification Test Suite for Milestone 1.
Challenger: teamwork_challenger (adversarial review & empirical verification).

Mandates:
1. Read directly from `resources/văn bản mẫu/vpub/Hợp lệ` (bypassing any cached intermediate JSON/CSV).
2. Re-extract canonical 500 documents (13116 down to 12610), their `view.cpx` metadata,
   and their `kết_quả_gửi_đi.txt` attached send results.
3. Ingest all 500 rows directly from Google Sheet "Kết quả đích thực tế" via REST API.
4. Compute field-by-field diff across all 500 documents, asserting 0 mismatches.
5. Verify R2 compliance (untransformed handlers and followers).
6. Verify sheet structure (501 rows x 6 cols, frozen row 1, zero stray rows).
"""

import json
import os
import re
import sys
from pathlib import Path
import pytest
import requests

SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
TARGET_SHEET_NAME = "Kết quả đích thực tế"
TARGET_SHEET_ID = 991067123
SOURCE_TAB_NAME = "Thống kê"
TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SOURCE_DIR = Path(__file__).resolve().parent.parent / "resources" / "văn bản mẫu" / "vpub" / "Hợp lệ"

EXPECTED_HEADERS = [
    "STT",
    "Số hiệu văn bản",
    "Trích yếu",
    "Kết quả gửi đi kèm (Đích thực tế)",
    "Đơn vị nhận (Dữ liệu mẫu)",
    "Link liên kết đến tài liệu chính theo văn bản"
]


def get_token() -> str:
    """Retrieve or refresh Google OAuth access token directly."""
    if not TOKEN_PATH.exists():
        pytest.fail(f"Token file not found: {TOKEN_PATH}")
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    token_info = data.get("token", {})
    access_token = token_info.get("access_token")

    # Verify validity with lightweight call
    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=spreadsheetId"
    res = requests.get(test_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if res.status_code == 200:
        return access_token

    # Refresh
    refresh_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": data.get("client_id"),
        "client_secret": data.get("client_secret"),
        "refresh_token": token_info.get("refresh_token"),
        "grant_type": "refresh_token"
    }
    r = requests.post(refresh_url, data=payload, timeout=15)
    if r.status_code != 200:
        pytest.fail(f"Token refresh failed: {r.status_code} - {r.text}")
    new_token = r.json().get("access_token")
    token_info["access_token"] = new_token
    data["token"] = token_info
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return new_token


@pytest.fixture(scope="module")
def access_token():
    return get_token()


@pytest.fixture(scope="module")
def live_target_sheet(access_token):
    """Fetch live metadata and all rows from target sheet."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Properties
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    res_meta = requests.get(meta_url, headers=headers, timeout=15)
    assert res_meta.status_code == 200, f"Failed meta: {res_meta.text}"
    props = None
    for s in res_meta.json().get("sheets", []):
        p = s.get("properties", {})
        if p.get("sheetId") == TARGET_SHEET_ID:
            props = p
            break
    assert props is not None, f"Target sheet {TARGET_SHEET_ID} not found"

    # 2. Values A1:F600
    val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{TARGET_SHEET_NAME}'!A1:F600"
    res_val = requests.get(val_url, headers=headers, timeout=20)
    assert res_val.status_code == 200, f"Failed values: {res_val.text}"
    values = res_val.json().get("values", [])

    return {
        "properties": props,
        "header": values[0] if values else [],
        "data_rows": values[1:] if len(values) > 1 else []
    }


@pytest.fixture(scope="module")
def live_drive_links(access_token):
    """Fetch live drive links from 'Thống kê' tab A2:F5200."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{SOURCE_TAB_NAME}'!A2:F5200"
    res = requests.get(url, headers=headers, timeout=25)
    assert res.status_code == 200, f"Failed fetch Thống kê: {res.text}"
    rows = res.json().get("values", [])
    drive_links = {}
    for r in rows:
        if r and r[0].isdigit():
            drive_links[r[0]] = r[5] if len(r) > 5 else ""
    return drive_links


@pytest.fixture(scope="module")
def raw_source_catalog():
    """
    Directly parse raw documents from SOURCE_DIR without any cached JSON.
    Build mapping: signNumber -> (dir_name, ed_signNumber, ed_subject, raw_send_result, expected_receiver)
    """
    assert SOURCE_DIR.exists(), f"Source directory not found: {SOURCE_DIR}"
    all_dirs = [d for d in SOURCE_DIR.iterdir() if d.is_dir()]
    catalog = {}

    for d in all_dirs:
        cpx_path = d / "view.cpx"
        txt_path = d / "kết_quả_gửi_đi.txt"
        if not (cpx_path.exists() and txt_path.exists()):
            continue

        with open(cpx_path, "r", encoding="utf-8", errors="replace") as fp:
            cpx = json.load(fp)
        
        ed = cpx.get("ed") or {}
        sign = (ed.get("signNumber") or d.name).strip()
        subject = (ed.get("subject") or "").strip()
        send_result = txt_path.read_text(encoding="utf-8").strip()

        # Extract receiver from line 3 of txt or book.receiver
        receiver = ""
        for line in send_result.splitlines():
            if line.startswith("Đơn vị nhận:"):
                receiver = line[len("Đơn vị nhận:"):].strip()
                break
        if not receiver:
            receiver = ((cpx.get("book") or {}).get("receiver", "") or "").strip()

        catalog[sign] = {
            "dir_name": d.name,
            "sign": sign,
            "subject": subject,
            "send_result": send_result,
            "receiver": receiver
        }
    return catalog


def test_target_sheet_properties(live_target_sheet):
    """Verify target sheet grid properties: exactly 501 rows, 6 columns, frozen row 1."""
    props = live_target_sheet["properties"]
    grid = props.get("gridProperties", {})
    assert grid.get("rowCount") == 501, f"Expected rowCount 501, got {grid.get('rowCount')}"
    assert grid.get("columnCount") == 6, f"Expected columnCount 6, got {grid.get('columnCount')}"
    assert grid.get("frozenRowCount") == 1, f"Expected frozenRowCount 1, got {grid.get('frozenRowCount')}"


def test_target_sheet_header(live_target_sheet):
    """Verify exact header text and column order."""
    header = [h.strip() for h in live_target_sheet["header"]]
    assert header == EXPECTED_HEADERS, f"Header mismatch: {header} vs {EXPECTED_HEADERS}"


def test_target_sheet_exact_500_rows(live_target_sheet):
    """Verify that the target sheet contains exactly 500 document rows."""
    data_rows = live_target_sheet["data_rows"]
    assert len(data_rows) == 500, f"Expected 500 data rows, got {len(data_rows)}"


def test_no_stray_rows(access_token):
    """
    Adversarial check: Assert zero stray rows exist beyond row 501.
    1) An unbounded query of the worksheet returns exactly 501 rows.
    2) Requesting range beyond row 501 returns HTTP 400 (exceeds grid limits),
       proving the sheet is hard-bounded to exactly 501 rows.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Unbounded query
    url_all = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{TARGET_SHEET_NAME}'"
    res_all = requests.get(url_all, headers=headers, timeout=15)
    assert res_all.status_code == 200, f"Unbounded query failed: {res_all.text}"
    all_values = res_all.json().get("values", [])
    assert len(all_values) == 501, f"Expected exactly 501 rows in entire sheet, found {len(all_values)}"

    # 2. Exceeds grid limits test
    url_beyond = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{TARGET_SHEET_NAME}'!A502:F600"
    res_beyond = requests.get(url_beyond, headers=headers, timeout=15)
    assert res_beyond.status_code == 400, "Expected 400 for range exceeding grid limits"
    assert "exceeds grid limits" in res_beyond.text.lower()


def test_independent_ground_truth_diff_zero(live_target_sheet, raw_source_catalog, live_drive_links):
    """
    Core Verification: Computes exhaustive field-by-field diff across all 500 documents
    directly against raw filesystem source files and asserts ZERO diffs.
    """
    data_rows = live_target_sheet["data_rows"]
    diffs = []

    for idx, row in enumerate(data_rows, 1):
        stt = row[0].strip() if len(row) > 0 else ""
        sign = row[1].strip() if len(row) > 1 else ""
        subject = row[2].strip() if len(row) > 2 else ""
        send_result = row[3].strip() if len(row) > 3 else ""
        receiver = row[4].strip() if len(row) > 4 else ""
        drive_link = row[5].strip() if len(row) > 5 else ""

        # Check STT sequence
        if stt != str(idx):
            diffs.append({"row": idx, "field": "STT", "expected": str(idx), "actual": stt})

        # Check raw source document presence
        if sign not in raw_source_catalog:
            diffs.append({"row": idx, "field": "SIGN_NOT_IN_SOURCE", "expected": sign, "actual": "NOT_FOUND"})
            continue

        raw = raw_source_catalog[sign]

        # Field: Subject
        if subject != raw["subject"]:
            diffs.append({"row": idx, "field": "Trích yếu", "expected": raw["subject"], "actual": subject})

        # Field: Send result (normalized newline comparison)
        norm_actual_send = send_result.replace("\r\n", "\n").strip()
        norm_raw_send = raw["send_result"].replace("\r\n", "\n").strip()
        if norm_actual_send != norm_raw_send:
            diffs.append({
                "row": idx,
                "field": "Kết quả gửi đi kèm",
                "expected": norm_raw_send[:50],
                "actual": norm_actual_send[:50]
            })

        # Field: Receiver unit
        if receiver != raw["receiver"]:
            diffs.append({
                "row": idx,
                "field": "Đơn vị nhận",
                "expected": raw["receiver"],
                "actual": receiver
            })

        # Field: Drive link
        expected_link = live_drive_links.get(str(idx), "")
        if drive_link != expected_link:
            diffs.append({
                "row": idx,
                "field": "Link Drive",
                "expected": expected_link,
                "actual": drive_link
            })

    assert len(diffs) == 0, f"Found {len(diffs)} field mismatches! Details: {diffs[:10]}"


def test_r2_compliance_handlers_and_followers(live_target_sheet, raw_source_catalog):
    """
    R2 Compliance Verification:
    Asserts that 'Người xử lí' and 'Người theo dõi' lines are present verbatim in Col D
    and were not arbitrarily altered or discarded by lookup database validations.
    """
    data_rows = live_target_sheet["data_rows"]
    handler_count = 0
    follower_count = 0
    violations = []

    for idx, row in enumerate(data_rows, 1):
        sign = row[1].strip()
        send_text = row[3].strip() if len(row) > 3 else ""
        raw = raw_source_catalog.get(sign)
        assert raw is not None, f"Row {idx} sign {sign} not in catalog"

        raw_lines = [line.strip() for line in raw["send_result"].splitlines() if line.strip()]
        for line in raw_lines:
            if line.startswith("Người xử lí:"):
                handler_count += 1
                if line not in send_text:
                    violations.append((idx, sign, f"Missing handler line: {line}"))
            elif line.startswith("Người theo dõi:"):
                follower_count += 1
                if line not in send_text:
                    violations.append((idx, sign, f"Missing follower line: {line}"))

    # Assert exactly 500 handler lines and 500 follower lines checked
    assert handler_count == 500, f"Expected 500 handlers, verified {handler_count}"
    assert follower_count == 500, f"Expected 500 followers, verified {follower_count}"
    assert len(violations) == 0, f"R2 violations found: {violations[:5]}"


def test_edge_cases_empty_recipient_units(live_target_sheet):
    """
    Verify known edge cases STT 194 (12916/UBND-XDCT) and STT 229 (12881/UBND-KGVX),
    where source files have empty external recipients. Col E must be empty string.
    """
    data_rows = live_target_sheet["data_rows"]
    
    # STT 194 is at index 193
    row_194 = data_rows[193]
    assert row_194[0] == "194"
    assert row_194[1] == "12916/UBND-XDCT"
    assert row_194[4] == "", f"Expected empty Col E for STT 194, got: '{row_194[4]}'"

    # STT 229 is at index 228
    row_229 = data_rows[228]
    assert row_229[0] == "229"
    assert row_229[1] == "12881/UBND-KGVX"
    assert row_229[4] == "", f"Expected empty Col E for STT 229, got: '{row_229[4]}'"
