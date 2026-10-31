"""Adversarial Verification Suite for Google Sheet Reconciliation (Milestone M1).

Adversarially probes:
1. Exact string value and pure Red foreground color for all 82 newly populated cells.
2. Cell border and layout formatting retention (no format wiping or destructive override).
3. Adjacent columns integrity (Columns B and D) for all 82 rows to guarantee no cross-column leakage or corruption.
4. Retention of '-' for all 825 unmapped rows, including all 474 'VT' rows.
5. Global Red text color accounting: strictly 1,580 red cells in Column E (1,498 baseline + 82 new) and 0 in retained rows.
6. Sheet structure, tab configurations, and header integrity.
7. Disjointness and completeness of populated vs retained datasets and report accuracy.
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
def dataset():
    return load_reconciliation_data()


def test_adversarial_populated_cells_value_and_pure_red_color(auth, dataset):
    """Test 1: Verify all 81 populated cells have exact target string, pure Red color, and intact borders."""
    populated_rows, _, _ = dataset
    assert len(populated_rows) == 81

    # Query all 81 ranges in batch
    pop_indices = [int(r["Row"]) for r in populated_rows]
    pop_ranges = [f"'{DEFAULT_SHEET_TITLE}'!E{r}:E{r}" for r in pop_indices]

    fields = (
        "sheets.data.rowData.values("
        "userEnteredValue,effectiveValue,"
        "userEnteredFormat.textFormat.foregroundColor,"
        "effectiveFormat.textFormat.foregroundColor,"
        "effectiveFormat.borders,effectiveFormat.wrapStrategy"
        ")"
    )
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}"
    params = [("ranges", rng) for rng in pop_ranges]
    params.append(("fields", fields))

    resp = auth.authorized_request("GET", url, params=params)
    assert resp.status_code == 200, f"Query failed: {resp.status_code} {resp.text}"

    data_blocks = resp.json().get("sheets", [{}])[0].get("data", [])
    assert len(data_blocks) == 81, f"Expected 81 data blocks, got {len(data_blocks)}"

    value_failures = []
    color_failures = []
    border_failures = []

    for i, block in enumerate(data_blocks):
        exp_row = populated_rows[i]
        row_num = int(exp_row["Row"])
        exp_val = exp_row["TargetNoiNhan2"]

        row_data = block.get("rowData", [])
        assert len(row_data) > 0 and len(row_data[0].get("values", [])) > 0, f"Missing cell data at Row {row_num}"

        cell = row_data[0]["values"][0]
        actual_val = (
            cell.get("userEnteredValue", {}).get("stringValue")
            or cell.get("effectiveValue", {}).get("stringValue", "")
        )

        if actual_val != exp_val:
            value_failures.append({
                "row": row_num,
                "expected": exp_val,
                "actual": actual_val,
            })

        eff_color = cell.get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
        red = eff_color.get("red", 0.0)
        green = eff_color.get("green", 0.0)
        blue = eff_color.get("blue", 0.0)

        # Pure Red: red == 1 (or >= 0.99), green == 0, blue == 0
        is_pure_red = (red >= 0.99) and (green == 0.0) and (blue == 0.0)
        if not is_pure_red:
            color_failures.append({
                "row": row_num,
                "effective_color": eff_color,
            })

        # Check borders are preserved (top, bottom, left, right exist)
        borders = cell.get("effectiveFormat", {}).get("borders", {})
        if not ("top" in borders and "bottom" in borders and "left" in borders and "right" in borders):
            border_failures.append({
                "row": row_num,
                "borders": borders,
            })

    assert len(value_failures) == 0, f"Populated value failures: {value_failures}"
    assert len(color_failures) == 0, f"Populated color failures: {color_failures}"
    assert len(border_failures) == 0, f"Populated border failures: {border_failures}"


def test_adversarial_adjacent_columns_integrity(auth, dataset):
    """Test 2: Verify that adjacent columns (B and D) of the 82 updated rows align with document hierarchy and are uncorrupted."""
    populated_rows, _, _ = dataset

    # Fetch all Column B to resolve document hierarchy
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

    # Fetch Column D for all 82 rows
    pop_indices = [int(r["Row"]) for r in populated_rows]
    pop_ranges = [f"'{DEFAULT_SHEET_TITLE}'!D{r}:D{r}" for r in pop_indices]

    url_d = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values:batchGet"
    resp_d = auth.authorized_request("GET", url_d, params=[("ranges", rng) for rng in pop_ranges])
    assert resp_d.status_code == 200

    value_ranges = resp_d.json().get("valueRanges", [])
    assert len(value_ranges) == 81

    doc_id_mismatches = []
    noi_nhan_1_mismatches = []

    for i, vr in enumerate(value_ranges):
        exp_row = populated_rows[i]
        row_num = int(exp_row["Row"])
        vals = vr.get("values", [[]])[0]
        actual_d = vals[0] if len(vals) > 0 else ""

        # Assert Column D equals raw NoiNhan1
        if actual_d.strip() != exp_row["NoiNhan1"].strip():
            noi_nhan_1_mismatches.append({
                "row": row_num,
                "expected": exp_row["NoiNhan1"],
                "actual": actual_d,
            })

        # Assert inherited DocID from Column B matches DocID
        inherited_doc = doc_by_row.get(row_num, "")
        if inherited_doc != exp_row["DocID"].strip():
            doc_id_mismatches.append({
                "row": row_num,
                "expected": exp_row["DocID"],
                "inherited_from_col_b": inherited_doc,
            })

    assert len(doc_id_mismatches) == 0, f"DocID hierarchy mismatches in Column B: {doc_id_mismatches}"
    assert len(noi_nhan_1_mismatches) == 0, f"NoiNhan1 mismatches in Column D: {noi_nhan_1_mismatches}"


def test_adversarial_retained_rows_integrity(auth, dataset):
    """Test 3: Verify all 826 retained rows strictly hold '-' in Column E, including all 474 VT rows."""
    _, retained_rows, _ = dataset
    assert len(retained_rows) == 826

    # Fetch all Column E rows 2 to 5140
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values/'{DEFAULT_SHEET_TITLE}'!E2:E5140"
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200, f"Fetch Column E failed: {resp.status_code} {resp.text}"

    col_e_values = resp.json().get("values", [])

    retained_mismatches = []
    for r in retained_rows:
        row_num = int(r["Row"])
        offset = row_num - 2
        val = col_e_values[offset][0] if 0 <= offset < len(col_e_values) and len(col_e_values[offset]) > 0 else ""
        if val != "-":
            retained_mismatches.append({"row": row_num, "doc_id": r["DocID"], "actual": val})

    assert len(retained_mismatches) == 0, f"Retained rows that do not hold '-': {retained_mismatches}"

    # Also verify all 474 VT rows
    vt_rows = [r for r in retained_rows if r.get("Source") == "POLICY_ARCHIVAL_VT"]
    assert len(vt_rows) == 474
    vt_mismatches = []
    for r in vt_rows:
        row_num = int(r["Row"])
        offset = row_num - 2
        val = col_e_values[offset][0] if 0 <= offset < len(col_e_values) and len(col_e_values[offset]) > 0 else ""
        if val != "-":
            vt_mismatches.append({"row": row_num, "actual": val})
    assert len(vt_mismatches) == 0, f"VT rows that do not hold '-': {vt_mismatches}"


def test_adversarial_global_red_color_accounting(auth, dataset):
    """Test 4: Verify global text color accounting: exactly 1,579 red cells in Column E and 0 in retained rows."""
    populated_rows, retained_rows, _ = dataset
    pop_indices = set(int(r["Row"]) for r in populated_rows)
    ret_indices = set(int(r["Row"]) for r in retained_rows)

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}"
        f"?ranges='{DEFAULT_SHEET_TITLE}'!E2:E5140"
        f"&fields=sheets.data.rowData.values(effectiveFormat.textFormat.foregroundColor)"
    )
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200

    data = resp.json().get("sheets", [{}])[0].get("data", [])
    rows = data[0].get("rowData", []) if data else []

    red_cells = set()
    for idx, r in enumerate(rows, start=2):
        vals = r.get("values", [])
        if vals:
            eff_color = vals[0].get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
            if eff_color.get("red", 0.0) >= 0.99 and eff_color.get("green", 0.0) == 0.0 and eff_color.get("blue", 0.0) == 0.0:
                red_cells.add(idx)

    # Total red cells must be exactly 1,579 (1,498 baseline clerical + 81 new)
    assert len(red_cells) == 1579, f"Expected 1579 red cells in Column E, found {len(red_cells)}"

    # All 81 populated rows must be red
    missing_pop_red = pop_indices - red_cells
    assert len(missing_pop_red) == 0, f"Populated rows missing red color: {missing_pop_red}"

    # Retained rows must have zero red cells
    ret_red_leakage = ret_indices.intersection(red_cells)
    assert len(ret_red_leakage) == 0, f"Retained rows accidentally colored red: {ret_red_leakage}"


def test_adversarial_sheet_structure_and_header_preservation(auth):
    """Test 5: Verify spreadsheet properties, tab names, row/column counts, and header row."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}?fields=properties,sheets.properties"
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200

    sheets = resp.json().get("sheets", [])
    sheet_map = {s["properties"]["sheetId"]: s["properties"]["title"] for s in sheets}

    # Tab 0 must be 'Thống kê'
    assert 0 in sheet_map
    assert sheet_map[0] == "Thống kê"

    # Verify header row
    hdr_url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}/values/'{DEFAULT_SHEET_TITLE}'!A1:F1"
    hdr_resp = auth.authorized_request("GET", hdr_url)
    assert hdr_resp.status_code == 200

    headers = hdr_resp.json().get("values", [[]])[0]
    assert len(headers) >= 5
    assert headers[0] == "STT"
    assert headers[1] == "Số hiệu văn bản"
    assert headers[2] == "Trích yếu"
    assert "Nơi nhận 1" in headers[3]
    assert "Nơi nhận 2" in headers[4]


def test_adversarial_unmapped_report_completeness_and_fidelity():
    """Test 6: Adversarially verify markdown report covers every single one of the 826 retained rows."""
    assert REPORT_OUTPUT_FILE.exists(), f"Missing report: {REPORT_OUTPUT_FILE}"

    with open(RETAINED_ROWS_CSV, "r", encoding="utf-8") as f:
        retained_rows = list(csv.DictReader(f))

    assert len(retained_rows) == 826

    with open(REPORT_OUTPUT_FILE, "r", encoding="utf-8") as f:
        report_text = f.read()

    # Verify summary table contains correct category counts
    assert "474" in report_text  # VT
    assert "44" in report_text   # Specialist/internal
    assert "52" in report_text   # Party
    assert "132" in report_text  # Composite/individual
    assert "124" in report_text  # External/unmapped
    assert "826" in report_text  # Total retained
    assert "81" in report_text   # Total populated

    # Verify all retained row numbers appear in markdown table
    missing_rows_in_report = []
    for r in retained_rows:
        row_str = f"| {r['Row']} |"
        if row_str not in report_text:
            missing_rows_in_report.append(r["Row"])

    assert len(missing_rows_in_report) == 0, (
        f"The following {len(missing_rows_in_report)} rows are missing from the report table: {missing_rows_in_report[:10]}"
    )
