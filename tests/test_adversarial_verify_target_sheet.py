"""
tests/test_adversarial_verify_target_sheet.py

Adversarial Stress Test Suite for Live Google Spreadsheet Tab "Kết quả đích thực tế"
Target Spreadsheet ID: 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s
Worksheet ID: 991067123
"""

import sys
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from tools.adversarial_verify_target_sheet import (
    run_adversarial_verification,
    SPREADSHEET_ID,
    TARGET_SHEET_NAME,
    TARGET_SHEET_ID,
)


@pytest.fixture(scope="module")
def adversarial_results():
    """Run full empirical adversarial verification suite once for module."""
    return run_adversarial_verification()


def test_adversarial_boundary_and_dimensions(adversarial_results):
    """Assert strict boundary dimensions and grid bounds."""
    bt = adversarial_results["boundary_tests"]
    assert bt["rowCount"] == 501, f"Expected exactly 501 rows in grid, got {bt['rowCount']}"
    assert bt["columnCount"] == 6, f"Expected exactly 6 columns in grid, got {bt['columnCount']}"
    assert bt["frozenRowCount"] == 1, f"Expected 1 frozen header row, got {bt['frozenRowCount']}"
    assert bt["merges_count"] == 0, f"Expected 0 merged cell ranges, got {bt['merges_count']}"
    assert "EXCEEDS_GRID_LIMITS" in bt["row_502_check"], f"Row 502 check failed: {bt['row_502_check']}"
    assert "EXCEEDS_GRID_LIMITS" in bt["col_G_check"], f"Col G check failed: {bt['col_G_check']}"
    assert bt["header_match"] == "PASSED"
    assert bt["row_501_stt500_match"] == "PASSED"


def test_adversarial_nullness_and_completeness(adversarial_results):
    """Assert zero unintended null cells across all 500 document rows."""
    nt = adversarial_results["nullness_tests"]
    assert nt["stt_nulls"] == 0, "STT column contains null/empty cells"
    assert nt["so_hieu_nulls"] == 0, "Số hiệu column contains null/empty cells"
    assert nt["trich_yeu_nulls"] == 0, "Trích yếu column contains null/empty cells"
    assert nt["ket_qua_nulls"] == 0, "Kết quả gửi column contains null/empty cells"
    assert nt["drive_link_nulls"] == 0, "Drive Link column contains null/empty cells"
    # Exactly rows 194 & 229 empty in source
    assert nt["don_vi_nhan_nulls"] == 2, f"Expected 2 empty recipient cells, got {nt['don_vi_nhan_nulls']}"
    assert nt["empty_dvn_rows"] == [194, 229], f"Unexpected empty recipient rows: {nt['empty_dvn_rows']}"


def test_adversarial_google_drive_urls(adversarial_results):
    """Assert URL format, uniqueness, and HTTP accessibility."""
    dut = adversarial_results["drive_url_tests"]
    assert dut["total_urls"] == 500, f"Expected 500 URLs, got {dut['total_urls']}"
    assert dut["invalid_format_count"] == 0, f"Invalid format count: {dut['invalid_format_count']}"
    assert dut["unique_urls_count"] == 500, f"Expected 500 unique URLs, got {dut['unique_urls_count']}"
    assert dut["unique_file_ids_count"] == 500, f"Expected 500 unique file IDs, got {dut['unique_file_ids_count']}"

    # Sample HTTP status checks
    for stt, status in dut["sample_http_status"].items():
        assert status in (200, 302), f"Drive URL for STT {stt} returned HTTP status: {status}"


def test_adversarial_formatting_and_styling(adversarial_results):
    """Assert header styling, column widths, and visual presentation."""
    fmt = adversarial_results["formatting_tests"]
    assert fmt["column_widths"] == [60, 160, 350, 380, 380, 260], (
        f"Column widths mismatch: {fmt['column_widths']}"
    )
    assert fmt["header_cells_count"] == 6


def test_adversarial_spot_check_50_documents(adversarial_results):
    """Assert 100% field fidelity across 50 randomly sampled documents."""
    sc = adversarial_results["spot_check_50_tests"]
    assert sc["sample_count"] == 50, f"Expected 50 sample documents, got {sc['sample_count']}"
    assert sc["error_count"] == 0, f"Spot-check errors found: {sc['error_count']}"
    assert sc["matched_count"] == 50, f"Matched count: {sc['matched_count']}/50"


def test_adversarial_final_verdict(adversarial_results):
    """Assert that overall verdict is APPROVE with zero failures."""
    assert adversarial_results["overall_status"] == "APPROVE"
    assert len(adversarial_results["failures"]) == 0, f"Failures: {adversarial_results['failures']}"
