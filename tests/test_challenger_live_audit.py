"""Independent Empirical Challenger Verification Suite for Live Google Spreadsheet.

Spreadsheet ID: 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s
Sheet: 'Thống kê' (sheetId: 0)
Milestone: M1 Iteration 2 Defect Remediation Audit

This test module executes direct queries against Google Sheets API and verifies:
1. All 81 populated cells have exact target string, pure Red foreground color, intact borders, and WRAP strategy.
2. Defect rows:
   - Rows 1065, 1097, 4493, 4611: exactly "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai" in red font.
   - Row 805: exactly "-" with NO red font.
   - Row 896: exactly 3 PMBs separated by ";" in red font.
   - Rows 880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812 (9 rows):
     exactly "Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai" in red font.
3. Total red cell count across Column E ('Thống kê'!E2:E5140) is strictly 1,579.
4. All 826 retained rows strictly contain "-".
5. Adjacent columns B (DocID) and D (NoiNhan1) integrity for all 81 populated rows.
6. Reconciliation datasets and unmapped recipients report consistency.
"""

import csv
import json
from pathlib import Path
import pytest
import requests

from tools.reconcile_sheet import (
    DEFAULT_SPREADSHEET_ID,
    DEFAULT_SHEET_TITLE,
    POPULATED_ROWS_CSV,
    RETAINED_ROWS_CSV,
    DECISIONS_JSON,
    REPORT_OUTPUT_FILE,
    GoogleSheetsAuth,
    load_reconciliation_data,
)


@pytest.fixture(scope="module")
def auth():
    return GoogleSheetsAuth()


@pytest.fixture(scope="module")
def recon_data():
    return load_reconciliation_data()


def test_challenger_dataset_counts(recon_data):
    """Verify exact counts in reconciliation dataset files."""
    populated_rows, retained_rows, decisions = recon_data
    assert len(populated_rows) == 81, f"Expected 81 populated rows, got {len(populated_rows)}"
    assert len(retained_rows) == 826, f"Expected 826 retained rows, got {len(retained_rows)}"

    summary = decisions.get("summary", {})
    assert summary.get("total_unmapped") == 907
    assert summary.get("total_populated") == 81
    assert summary.get("total_retained_dash") == 826

    pop_rows_set = {int(r["Row"]) for r in populated_rows}
    ret_rows_set = {int(r["Row"]) for r in retained_rows}
    assert len(pop_rows_set) == 81, "Duplicate row IDs in populated_rows.csv"
    assert len(ret_rows_set) == 826, "Duplicate row IDs in retained_rows.csv"
    assert len(pop_rows_set.intersection(ret_rows_set)) == 0, "Intersection between populated and retained"


def test_challenger_live_remediated_defects(auth):
    """Specifically verify the 15 remediated defect rows directly from Google Sheets API."""
    remediated_party_rows = [1065, 1097, 4493, 4611]
    remediated_joint_rows = [880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812]
    all_check_rows = [805, 896] + remediated_party_rows + remediated_joint_rows

    ranges = [f"'{DEFAULT_SHEET_TITLE}'!D{r}:E{r}" for r in all_check_rows]
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}"
        f"?ranges=" + "&ranges=".join(ranges) +
        "&fields=sheets.data.rowData.values(userEnteredValue,effectiveValue,effectiveFormat.textFormat.foregroundColor)"
    )
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200, f"Failed to fetch defect ranges: {resp.status_code} {resp.text}"

    data_blocks = resp.json().get("sheets", [{}])[0].get("data", [])
    assert len(data_blocks) == len(all_check_rows)

    results = {}
    for r_num, block in zip(all_check_rows, data_blocks):
        vals = block.get("rowData", [{}])[0].get("values", [{}, {}])
        d_val = vals[0].get("userEnteredValue", {}).get("stringValue", "")
        e_val = vals[1].get("userEnteredValue", {}).get("stringValue", "")
        eff_color = vals[1].get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
        results[r_num] = {"d": d_val, "e": e_val, "color": eff_color}

    # 1. Row 805: Truyền tải điện 3 -> MUST BE "-" AND NOT RED
    r805 = results[805]
    assert r805["d"] == "Truyền tải điện 3", f"Row 805 Col D expected 'Truyền tải điện 3', got '{r805['d']}'"
    assert r805["e"] == "-", f"Row 805 Col E expected '-', got '{r805['e']}'"
    red_805 = r805["color"].get("red", 0.0)
    assert red_805 < 0.99, f"Row 805 must NOT have red font, got red={red_805}"

    # 2. Rows 1065, 1097, 4493, 4611: Văn phòng Đảng ủy UBND tỉnh -> "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai" in red font
    expected_party = "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai"
    for r_num in remediated_party_rows:
        r_data = results[r_num]
        assert r_data["d"] == "Văn phòng Đảng ủy UBND tỉnh", f"Row {r_num} Col D expected 'Văn phòng Đảng ủy UBND tỉnh', got '{r_data['d']}'"
        assert r_data["e"] == expected_party, f"Row {r_num} Col E expected '{expected_party}', got '{r_data['e']}'"
        assert not r_data["e"].endswith(";"), f"Row {r_num} Col E has invalid trailing semicolon: '{r_data['e']}'"
        assert "ĐBQH" not in r_data["e"], f"Row {r_num} Col E incorrectly mentions legislative council"
        assert r_data["color"].get("red", 0.0) >= 0.99, f"Row {r_num} must have red font, got {r_data['color']}"
        assert r_data["color"].get("green", 0.0) == 0.0
        assert r_data["color"].get("blue", 0.0) == 0.0

    # 3. Row 896: Các Ban QLDA thuộc tỉnh -> 3 PMBs in red font
    r896 = results[896]
    assert r896["d"] == "Các Ban QLDA thuộc tỉnh"
    expected_pmb_tokens = [
        "Ban QLDA các công trình Giao thông và Dân dụng tỉnh Gia Lai",
        "Ban Quản lý Dự án Nông nghiệp và Phát triển nông thôn tỉnh Gia Lai",
        "Ban Quản lý các dự án đầu tư xây dựng tỉnh Gia Lai",
    ]
    actual_pmbs = r896["e"].split(";")
    assert len(actual_pmbs) == 3, f"Row 896 expected 3 PMBs, got {len(actual_pmbs)}: {actual_pmbs}"
    for expected_token in expected_pmb_tokens:
        assert expected_token in actual_pmbs, f"Row 896 missing PMB '{expected_token}'"
    assert r896["color"].get("red", 0.0) >= 0.99, f"Row 896 must have red font, got {r896['color']}"

    # 4. Rows 880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812: Dual Offices in red font
    expected_joint = "Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
    for r_num in remediated_joint_rows:
        r_data = results[r_num]
        assert r_data["d"] == "Các VP: Tỉnh uỷ, Đoàn ĐBQH và HĐND tỉnh", f"Row {r_num} Col D unexpected: '{r_data['d']}'"
        assert r_data["e"] == expected_joint, f"Row {r_num} Col E expected '{expected_joint}', got '{r_data['e']}'"
        tokens = r_data["e"].split(";")
        assert len(tokens) == 2, f"Row {r_num} expected 2 tokens, got {len(tokens)}"
        assert tokens[0] == "Văn phòng Tỉnh ủy"
        assert tokens[1] == "Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
        assert r_data["color"].get("red", 0.0) >= 0.99, f"Row {r_num} must have red font, got {r_data['color']}"


def test_challenger_all_81_populated_cells_formatting_and_borders(auth, recon_data):
    """Adversarially verify all 81 populated cells: value, red color, borders, wrap strategy, no trailing semicolons."""
    populated_rows, _, _ = recon_data
    assert len(populated_rows) == 81

    ranges = [f"'{DEFAULT_SHEET_TITLE}'!E{r['Row']}:E{r['Row']}" for r in populated_rows]
    fields = (
        "sheets.data.rowData.values("
        "userEnteredValue,effectiveValue,"
        "effectiveFormat.textFormat.foregroundColor,"
        "effectiveFormat.borders,effectiveFormat.wrapStrategy"
        ")"
    )
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}"
    resp = auth.authorized_request("GET", url, params=[("ranges", r) for r in ranges] + [("fields", fields)])
    assert resp.status_code == 200, f"Query failed: {resp.status_code} {resp.text}"

    data_blocks = resp.json().get("sheets", [{}])[0].get("data", [])
    assert len(data_blocks) == 81

    discrepancies = []
    for i, (pop_meta, block) in enumerate(zip(populated_rows, data_blocks)):
        row_num = int(pop_meta["Row"])
        exp_val = pop_meta["TargetNoiNhan2"]

        row_vals = block.get("rowData", [{}])[0].get("values", [{}])
        cell = row_vals[0] if row_vals else {}

        actual_val = cell.get("userEnteredValue", {}).get("stringValue") or cell.get("effectiveValue", {}).get("stringValue", "")
        eff_format = cell.get("effectiveFormat", {})
        eff_color = eff_format.get("textFormat", {}).get("foregroundColor", {})
        borders = eff_format.get("borders", {})
        wrap_strat = eff_format.get("wrapStrategy", "")

        # Value check
        if actual_val != exp_val:
            discrepancies.append(f"Row {row_num}: value mismatch: expected '{exp_val}', got '{actual_val}'")

        # Syntax check on populated string
        if actual_val.endswith(";"):
            discrepancies.append(f"Row {row_num}: trailing semicolon in value '{actual_val}'")
        if actual_val.startswith(";"):
            discrepancies.append(f"Row {row_num}: leading semicolon in value '{actual_val}'")
        if ";;" in actual_val:
            discrepancies.append(f"Row {row_num}: empty token ';;' in value '{actual_val}'")
        for token in actual_val.split(";"):
            if not token.strip():
                discrepancies.append(f"Row {row_num}: blank sub-token in value '{actual_val}'")

        # Color check: pure red
        red = eff_color.get("red", 0.0)
        green = eff_color.get("green", 0.0)
        blue = eff_color.get("blue", 0.0)
        if not (red >= 0.99 and green == 0.0 and blue == 0.0):
            discrepancies.append(f"Row {row_num}: color is not pure red: {eff_color}")

        # Borders check: top, bottom, left, right must exist
        for side in ["top", "bottom", "left", "right"]:
            if side not in borders:
                discrepancies.append(f"Row {row_num}: missing border side '{side}'")

        # Text wrapping check
        if wrap_strat != "WRAP":
            discrepancies.append(f"Row {row_num}: wrapStrategy is not 'WRAP', got '{wrap_strat}'")

    assert len(discrepancies) == 0, f"Found {len(discrepancies)} discrepancies across 81 populated cells:\n" + "\n".join(discrepancies[:20])


def test_challenger_global_red_cells_count_strictly_1579(auth, recon_data):
    """Adversarially verify that total red cells across Column E is strictly 1,579."""
    populated_rows, retained_rows, _ = recon_data
    pop_row_numbers = set(int(r["Row"]) for r in populated_rows)
    ret_row_numbers = set(int(r["Row"]) for r in retained_rows)

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}"
        f"?ranges='{DEFAULT_SHEET_TITLE}'!E2:E5140"
        f"&fields=sheets.data.rowData.values(effectiveFormat.textFormat.foregroundColor)"
    )
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200

    data = resp.json().get("sheets", [{}])[0].get("data", [])
    rows = data[0].get("rowData", []) if data else []

    red_rows = set()
    for idx, r in enumerate(rows, start=2):
        vals = r.get("values", [])
        if vals:
            eff_color = vals[0].get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
            if eff_color.get("red", 0.0) >= 0.99 and eff_color.get("green", 0.0) == 0.0 and eff_color.get("blue", 0.0) == 0.0:
                red_rows.add(idx)

    # 1. Total count assertion
    assert len(red_rows) == 1579, (
        f"CRITICAL DISCREPANCY: Expected strictly 1,579 red cells in Column E, but found {len(red_rows)}!"
    )

    # 2. All 81 newly populated cells must be red
    missing_pop_red = pop_row_numbers - red_rows
    assert len(missing_pop_red) == 0, f"Populated rows missing red font: {missing_pop_red}"

    # 3. Exactly 1498 baseline clerical red cells
    baseline_red = red_rows - pop_row_numbers
    assert len(baseline_red) == 1498, f"Expected 1,498 baseline clerical red cells, got {len(baseline_red)}"

    # 4. Zero retained rows can be red
    leakage = ret_row_numbers.intersection(red_rows)
    assert len(leakage) == 0, f"Retained rows unexpectedly colored red: {leakage}"

    # 5. Row 805 must not be red
    assert 805 not in red_rows, "Row 805 must NOT be red"


def test_challenger_all_826_retained_rows_contain_dash(auth, recon_data):
    """Adversarially verify that all 826 retained rows strictly contain '-' in Column E."""
    _, retained_rows, _ = recon_data
    assert len(retained_rows) == 826

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values/'{DEFAULT_SHEET_TITLE}'!E2:E5140"
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200

    col_e_values = resp.json().get("values", [])
    non_dash_rows = []

    for r in retained_rows:
        row_num = int(r["Row"])
        offset = row_num - 2
        val = col_e_values[offset][0] if 0 <= offset < len(col_e_values) and len(col_e_values[offset]) > 0 else ""
        if val != "-":
            non_dash_rows.append({"row": row_num, "doc_id": r.get("DocID"), "actual": val})

    assert len(non_dash_rows) == 0, f"Found {len(non_dash_rows)} retained rows that do not hold '-': {non_dash_rows[:10]}"

    # Specifically check all 474 VT rows
    vt_rows = [r for r in retained_rows if r.get("Source") == "POLICY_ARCHIVAL_VT"]
    assert len(vt_rows) == 474, f"Expected 474 VT rows, got {len(vt_rows)}"
    vt_non_dash = []
    for r in vt_rows:
        row_num = int(r["Row"])
        offset = row_num - 2
        val = col_e_values[offset][0] if 0 <= offset < len(col_e_values) and len(col_e_values[offset]) > 0 else ""
        if val != "-":
            vt_non_dash.append({"row": row_num, "actual": val})
    assert len(vt_non_dash) == 0, f"Found {len(vt_non_dash)} VT rows not holding '-': {vt_non_dash}"


def test_challenger_adjacent_columns_alignment(auth, recon_data):
    """Verify Column D ('Nơi nhận 1') and Column B ('Số hiệu văn bản') for all 81 populated rows."""
    populated_rows, _, _ = recon_data

    # Fetch Column B to reconstruct document hierarchy
    url_b = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values/'{DEFAULT_SHEET_TITLE}'!B2:B5140"
    resp_b = auth.authorized_request("GET", url_b)
    assert resp_b.status_code == 200
    col_b_values = [r[0] if len(r) > 0 else "" for r in resp_b.json().get("values", [])]

    current_doc = ""
    doc_by_row = {}
    for idx, val in enumerate(col_b_values, start=2):
        if val.strip():
            current_doc = val.strip()
        doc_by_row[idx] = current_doc

    ranges = [f"'{DEFAULT_SHEET_TITLE}'!D{r['Row']}:D{r['Row']}" for r in populated_rows]
    url_d = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values:batchGet"
    resp_d = auth.authorized_request("GET", url_d, params=[("ranges", rng) for rng in ranges])
    assert resp_d.status_code == 200

    value_ranges = resp_d.json().get("valueRanges", [])
    assert len(value_ranges) == 81

    alignment_errors = []
    for i, vr in enumerate(value_ranges):
        meta = populated_rows[i]
        row_num = int(meta["Row"])
        vals = vr.get("values", [[]])[0]
        actual_d = vals[0] if len(vals) > 0 else ""

        # Column D text check
        if actual_d.strip() != meta["NoiNhan1"].strip():
            alignment_errors.append(f"Row {row_num} Col D mismatch: expected '{meta['NoiNhan1']}', got '{actual_d}'")

        # Column B inherited DocID check
        inherited_doc = doc_by_row.get(row_num, "")
        if inherited_doc != meta["DocID"].strip():
            alignment_errors.append(f"Row {row_num} DocID mismatch: expected '{meta['DocID']}', got '{inherited_doc}'")

    assert len(alignment_errors) == 0, f"Found {len(alignment_errors)} alignment errors:\n" + "\n".join(alignment_errors)


def test_challenger_unmapped_report_completeness():
    """Verify that the unmapped report strictly accounts for all 826 retained rows."""
    assert REPORT_OUTPUT_FILE.exists(), f"Report file not found: {REPORT_OUTPUT_FILE}"

    with open(RETAINED_ROWS_CSV, "r", encoding="utf-8") as f:
        retained_rows = list(csv.DictReader(f))
    assert len(retained_rows) == 826

    with open(REPORT_OUTPUT_FILE, "r", encoding="utf-8") as f:
        report_text = f.read()

    # Check summary counts
    assert "826" in report_text
    assert "81" in report_text
    assert "474" in report_text  # VT
    assert "44" in report_text   # Specialist
    assert "52" in report_text   # Party
    assert "132" in report_text  # Composite
    assert "124" in report_text  # External

    # Check Row 805 is documented
    assert "| 805 |" in report_text
    assert "Truyền tải điện 3" in report_text

    # Check all 826 rows exist in markdown table
    missing_rows = [r["Row"] for r in retained_rows if f"| {r['Row']} |" not in report_text]
    assert len(missing_rows) == 0, f"Report missing {len(missing_rows)} rows: {missing_rows[:10]}"
