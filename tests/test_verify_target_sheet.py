"""
tests/test_verify_target_sheet.py

Pytest Test Suite for Live Verification of Google Spreadsheet Tab "Kết quả đích thực tế"
(Worksheet ID: 991067123 in Spreadsheet: 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s)

Verifies:
- Live Sheet Accessibility & OAuth Status
- Sheet Grid Properties (501 rows x 6 columns, frozen header)
- Exact 500 Document Rows (STT 1 to 500)
- 100% Field Fidelity against Ground Truth Source Files (view.cpx, kết_quả_gửi_đi.txt)
- R2 Compliance: Unconstrained handling of "Người xử lí", "Người theo dõi", "Đơn vị nhận"
- Google Drive Link integrity and format
"""

import sys
import pytest
from pathlib import Path

# Ensure project root is on sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from tools.verify_target_sheet import (
    SPREADSHEET_ID,
    TARGET_SHEET_NAME,
    TARGET_SHEET_ID,
    EXPECTED_HEADERS,
    fetch_live_sheet_data,
    verify_live_sheet,
    normalize_text,
)


@pytest.fixture(scope="module")
def live_sheet_data():
    """Module-level fixture to fetch live sheet data once for all test assertions."""
    header, data_rows, props = fetch_live_sheet_data()
    return {
        "header": header,
        "data_rows": data_rows,
        "props": props
    }


def test_target_sheet_grid_properties(live_sheet_data):
    """Verify worksheet metadata, grid dimensions, and frozen header."""
    props = live_sheet_data["props"]
    assert props.get("sheetId") == TARGET_SHEET_ID
    assert props.get("title") == TARGET_SHEET_NAME

    grid = props.get("gridProperties", {})
    assert grid.get("rowCount") == 501, f"Expected 501 rows in grid, got {grid.get('rowCount')}"
    assert grid.get("columnCount") == 6, f"Expected 6 columns in grid, got {grid.get('columnCount')}"
    assert grid.get("frozenRowCount") == 1, f"Expected 1 frozen header row, got {grid.get('frozenRowCount')}"


def test_target_sheet_headers(live_sheet_data):
    """Verify exact match of header columns against canonical schema."""
    header = [h.strip() for h in live_sheet_data["header"]]
    assert len(header) == 6, f"Expected 6 header columns, got {len(header)}"
    assert header == EXPECTED_HEADERS, f"Header mismatch: {header} vs {EXPECTED_HEADERS}"


def test_target_sheet_exact_500_document_rows(live_sheet_data):
    """Verify exactly 500 document data rows are populated (rows 2..501)."""
    data_rows = live_sheet_data["data_rows"]
    assert len(data_rows) == 500, f"Expected exactly 500 data rows, got {len(data_rows)}"

    # Verify no completely empty rows exist within the 500 rows
    for idx, row in enumerate(data_rows, 1):
        assert any(cell.strip() for cell in row), f"Row {idx} is unexpectedly blank"


def test_target_sheet_anchors(live_sheet_data):
    """Verify first document (STT 1: 13116) and last document (STT 500: 12610)."""
    data_rows = live_sheet_data["data_rows"]

    # First row (STT 1)
    row_1 = data_rows[0]
    assert row_1[0].strip() == "1"
    assert "13116/UBND-TD" in row_1[1]
    assert "Thanh tra" in row_1[2]

    # Last row (STT 500)
    row_500 = data_rows[499]
    assert row_500[0].strip() == "500"
    assert "12610/UBND-NNMT" in row_500[1]


def test_r2_compliance_unconstrained_handling(live_sheet_data):
    """
    Verify R2 compliance:
    'Không cần bận tâm người xử lí, người theo dõi, đơn vị nhận.
     Nhóm tự xác định cấu trúc cột dựa trên bố cục có sẵn của trang tính...'
    Asserts that internal handlers, observers, and destination units are preserved
    as authentic raw ground truth without rejection or database schema distortion.
    """
    data_rows = live_sheet_data["data_rows"]

    # Check that Column D contains the full unconstrained ground truth text
    # containing 'Người xử lí:' and 'Người theo dõi:'
    row_1_col_d = data_rows[0][3]
    assert "Người xử lí:" in row_1_col_d, "Col D must contain raw 'Người xử lí:' data"
    assert "Người theo dõi:" in row_1_col_d, "Col D must contain raw 'Người theo dõi:' data"
    assert "Đơn vị nhận:" in row_1_col_d, "Col D must contain raw 'Đơn vị nhận:' data"

    # Confirm that Column E presents the destination units for sample evaluation
    row_1_col_e = data_rows[0][4]
    assert len(row_1_col_e) > 0, "Col E must contain destination units"
    assert "Trung tâm Phục vụ hành chính công" in row_1_col_e


def test_google_drive_links_integrity(live_sheet_data):
    """Verify that all 500 documents contain valid Google Drive web view URLs."""
    data_rows = live_sheet_data["data_rows"]

    for idx, row in enumerate(data_rows, 1):
        padded_row = row + [""] * (6 - len(row))
        link = padded_row[5].strip()
        assert link.startswith("https://drive.google.com/file/d/"), (
            f"Row {idx} (STT {padded_row[0]}) has invalid Google Drive URL: '{link}'"
        )
        assert link.endswith("/view"), (
            f"Row {idx} (STT {padded_row[0]}) Drive link does not end with '/view': '{link}'"
        )


def test_100_percent_field_fidelity_e2e():
    """
    Comprehensive End-to-End Test:
    Asserts 100% field fidelity across all 500 documents against the filesystem source files.
    """
    report = verify_live_sheet(verbose=False)
    assert report["passed"] is True, f"Verification failed with mismatches: {report['mismatches']}"
    assert report["total_data_rows"] == 500
    assert report["header_match"] is True

    fc = report["fidelity_checks"]
    assert fc["stt_match_count"] == 500, f"STT matches: {fc['stt_match_count']}/500"
    assert fc["so_hieu_match_count"] == 500, f"Số hiệu matches: {fc['so_hieu_match_count']}/500"
    assert fc["trich_yeu_match_count"] == 500, f"Trích yếu matches: {fc['trich_yeu_match_count']}/500"
    assert fc["ket_qua_gui_match_count"] == 500, f"Kết quả gửi matches: {fc['ket_qua_gui_match_count']}/500"
    assert fc["don_vi_nhan_match_count"] == 500, f"Đơn vị nhận matches: {fc['don_vi_nhan_match_count']}/500"
    assert fc["drive_link_match_count"] == 500, f"Drive link matches: {fc['drive_link_match_count']}/500"
    assert len(report["mismatches"]) == 0
