"""Unit and integration tests for Google Sheet Reconciliation & Report Generator."""

import csv
import json
from pathlib import Path
import pytest
from tools.reconcile_sheet import (
    DEFAULT_SPREADSHEET_ID,
    DEFAULT_SHEET_TITLE,
    POPULATED_ROWS_CSV,
    RETAINED_ROWS_CSV,
    DECISIONS_JSON,
    REPORT_OUTPUT_FILE,
    WORKER_REPORT_FILE,
    GoogleSheetsAuth,
    load_reconciliation_data,
    generate_unmapped_report,
    verify_live_sheet_updates,
)


def test_reconciliation_dataset_integrity():
    """Verify that populated and retained datasets are valid, complete, and mutually disjoint."""
    assert POPULATED_ROWS_CSV.exists(), "populated_rows.csv does not exist"
    assert RETAINED_ROWS_CSV.exists(), "retained_rows.csv does not exist"
    assert DECISIONS_JSON.exists(), "reconciliation_decisions.json does not exist"

    populated_rows, retained_rows, decisions = load_reconciliation_data()

    # Exact count checks: 81 populated, 826 retained
    assert len(populated_rows) == 81, f"Expected 81 populated rows, got {len(populated_rows)}"
    assert len(retained_rows) == 826, f"Expected 826 retained rows, got {len(retained_rows)}"

    pop_indices = [int(r["Row"]) for r in populated_rows]
    ret_indices = [int(r["Row"]) for r in retained_rows]

    # No internal duplicates
    assert len(pop_indices) == len(set(pop_indices)), "Duplicate rows in populated_rows.csv"
    assert len(ret_indices) == len(set(ret_indices)), "Duplicate rows in retained_rows.csv"

    # Mutually disjoint
    overlap = set(pop_indices).intersection(set(ret_indices))
    assert len(overlap) == 0, f"Found overlapping rows between populated and retained: {overlap}"

    # Total unmapped universe is 907
    total_unmapped = len(pop_indices) + len(ret_indices)
    assert total_unmapped == 907, f"Expected total 907 unmapped rows, got {total_unmapped}"

    # VT specific check: exactly 474 VT rows in retained
    vt_rows = [r for r in retained_rows if r.get("Source") == "POLICY_ARCHIVAL_VT"]
    assert len(vt_rows) == 474, f"Expected 474 VT rows, got {len(vt_rows)}"

    # External unmapped check: exactly 124 rows in retained (including row 805)
    ext_rows = [r for r in retained_rows if r.get("Source") == "UNMAPPED_EXTERNAL_OR_SPECIFIC"]
    assert len(ext_rows) == 124, f"Expected 124 external unmapped rows, got {len(ext_rows)}"


def test_reconciliation_semantic_accuracy():
    """Adversarially verify semantic correctness of key remediated rows against institutional reality."""
    populated_rows, retained_rows, decisions = load_reconciliation_data()
    pop_by_row = {int(r["Row"]): r for r in populated_rows}
    ret_by_row = {int(r["Row"]): r for r in retained_rows}

    # 1. Executive Party Committee rows (1065, 1097, 4493, 4611):
    # Must map to "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai" (not legislative council, no trailing semicolon)
    for r_num in [1065, 1097, 4493, 4611]:
        assert r_num in pop_by_row, f"Row {r_num} missing from populated_rows"
        val = pop_by_row[r_num]["TargetNoiNhan2"]
        assert val == "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai", f"Row {r_num} wrong value: {val}"
        assert not val.endswith(";"), f"Row {r_num} has invalid trailing semicolon: {val}"
        assert "ĐBQH" not in val, f"Row {r_num} conflated with legislative office: {val}"

    # 2. Row 805 (Truyền tải điện 3):
    # Must be retained as '-', NOT populated as Công ty Điện lực Gia Lai (PC Gia Lai is Row 804)
    assert 805 not in pop_by_row, "Row 805 must NOT be in populated_rows"
    assert 805 in ret_by_row, "Row 805 must be in retained_rows"
    assert ret_by_row[805]["Decision"] == "-", f"Row 805 decision must be '-', got {ret_by_row[805]['Decision']}"
    assert ret_by_row[805]["NoiNhan1"] == "Truyền tải điện 3"
    assert ret_by_row[805]["Source"] == "UNMAPPED_EXTERNAL_OR_SPECIFIC"

    # 3. Row 896 (Các Ban QLDA thuộc tỉnh):
    # Must contain all 3 provincial project management boards separated by ';'
    assert 896 in pop_by_row, "Row 896 missing from populated_rows"
    val_896 = pop_by_row[896]["TargetNoiNhan2"]
    assert "Ban QLDA các công trình Giao thông và Dân dụng tỉnh Gia Lai" in val_896
    assert "Ban Quản lý Dự án Nông nghiệp và Phát triển nông thôn tỉnh Gia Lai" in val_896
    assert "Ban Quản lý các dự án đầu tư xây dựng tỉnh Gia Lai" in val_896
    assert len(val_896.split(";")) == 3, f"Row 896 expected 3 PMBs, got {val_896.split(';')}"

    # 4. Joint Office rows (880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812):
    # Must contain BOTH "Văn phòng Tỉnh ủy" and "Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
    joint_rows = [880, 1107, 1891, 2097, 2132, 3719, 3747, 4676, 4812]
    expected_joint = "Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
    for r_num in joint_rows:
        assert r_num in pop_by_row, f"Row {r_num} missing from populated_rows"
        val = pop_by_row[r_num]["TargetNoiNhan2"]
        assert val == expected_joint, f"Row {r_num} expected '{expected_joint}', got '{val}'"
        assert "Văn phòng Tỉnh ủy" in val, f"Row {r_num} omitted Provincial Party Committee Office: {val}"
        assert "Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai" in val, f"Row {r_num} omitted Delegation/Council Office: {val}"


def test_unmapped_report_generation(tmp_path: Path):
    """Verify that unmapped report generates comprehensive sections and covers all 826 rows."""
    populated_rows, retained_rows, decisions = load_reconciliation_data()
    test_report_file = tmp_path / "test_report.md"

    content = generate_unmapped_report(retained_rows, decisions, test_report_file)

    assert test_report_file.exists()
    assert len(content) > 10000

    # Check key sections and counts
    assert "# Báo Cáo Tổng Hợp Các Dòng Chưa Ánh Xạ Nơi Nhận 2 ('-')" in content
    assert "POLICY_ARCHIVAL_VT" in content
    assert "826" in content
    assert "81" in content
    assert "474" in content
    assert "124" in content
    assert "| 805 |" in content
    assert "Truyền tải điện 3" in content

    # Check that production report exists and is valid
    assert REPORT_OUTPUT_FILE.exists(), f"Production report missing: {REPORT_OUTPUT_FILE}"
    assert WORKER_REPORT_FILE.exists(), f"Worker report copy missing: {WORKER_REPORT_FILE}"


def test_live_google_sheet_verification():
    """Verify live Google Sheet cells and Red text formatting directly against Google API."""
    auth = GoogleSheetsAuth()
    populated_rows, retained_rows, _ = load_reconciliation_data()

    results = verify_live_sheet_updates(
        auth=auth,
        spreadsheet_id=DEFAULT_SPREADSHEET_ID,
        sheet_title=DEFAULT_SHEET_TITLE,
        populated_rows=populated_rows,
        retained_rows=retained_rows,
    )

    assert results["populated_verified"] == 81, (
        f"Expected 81 verified populated rows, got {results['populated_verified']}. "
        f"Value mismatches: {results['populated_value_mismatches']}, "
        f"Color mismatches: {results['populated_color_mismatches']}"
    )
    assert len(results["populated_value_mismatches"]) == 0
    assert len(results["populated_color_mismatches"]) == 0

    assert results["retained_verified"] == 826, (
        f"Expected 826 verified retained rows, got {results['retained_verified']}. "
        f"Mismatches: {results['retained_mismatches']}"
    )
    assert len(results["retained_mismatches"]) == 0

    # Explicit live semantic spot-checks via Google Sheets API
    check_rows = [805, 880, 896, 1065, 1097, 4493, 4611]
    ranges = [f"'{DEFAULT_SHEET_TITLE}'!D{r}:E{r}" for r in check_rows]
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{DEFAULT_SPREADSHEET_ID}?ranges=" + "&ranges=".join(ranges) + "&fields=sheets.data.rowData.values(userEnteredValue,effectiveFormat.textFormat.foregroundColor)"
    res = auth.authorized_request("GET", url).json()

    live_vals = {}
    for b, r_num in zip(res["sheets"][0]["data"], check_rows):
        vals = b["rowData"][0]["values"]
        e_val = vals[1].get("userEnteredValue", {}).get("stringValue", "")
        col = vals[1].get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
        live_vals[r_num] = (e_val, col)

    # Row 805 must be '-' and NOT colored red
    assert live_vals[805][0] == "-", f"Live E805 expected '-', got {live_vals[805][0]}"
    assert live_vals[805][1].get("red", 0) < 0.99, f"Live E805 must not be red, got {live_vals[805][1]}"

    # Row 1065 must be 'Đảng ủy Ủy ban nhân dân tỉnh Gia Lai' in red
    assert live_vals[1065][0] == "Đảng ủy Ủy ban nhân dân tỉnh Gia Lai"
    assert live_vals[1065][1].get("red", 0) >= 0.99

    # Row 896 must have all 3 PMBs in red
    assert len(live_vals[896][0].split(";")) == 3
    assert live_vals[896][1].get("red", 0) >= 0.99

    # Row 880 must have both offices in red
    assert live_vals[880][0] == "Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai"
    assert live_vals[880][1].get("red", 0) >= 0.99
