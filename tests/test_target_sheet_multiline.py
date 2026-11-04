"""
tests/test_target_sheet_multiline.py

Pytest suite to verify the multiline formatting of tab 'Kết quả đích thực tế'
in Google Spreadsheet 1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s.
"""

import sys
import os
from pathlib import Path
import pytest

# Ensure tools directory is in sys.path
TEST_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = TEST_DIR.parent
sys.path.insert(0, str(WORKSPACE_DIR / "tools"))

from reconcile_sheet import GoogleSheetsAuth, DEFAULT_SPREADSHEET_ID

SPREADSHEET_ID = DEFAULT_SPREADSHEET_ID
TARGET_SHEET_NAME = "Kết quả đích thực tế"


@pytest.fixture(scope="module")
def sheet_data():
    auth = GoogleSheetsAuth()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{TARGET_SHEET_NAME}!A1:F501"
    resp = auth.authorized_request("GET", url)
    assert resp.status_code == 200, f"Failed to fetch values: {resp.text}"
    return resp.json().get("values", [])


def test_row_count_and_headers(sheet_data):
    assert len(sheet_data) == 501, f"Expected 501 rows, got {len(sheet_data)}"
    expected_header = [
        "STT",
        "Số hiệu văn bản",
        "Trích yếu",
        "Kết quả gửi đi kèm (Đích thực tế)",
        "Đơn vị nhận (Dữ liệu mẫu)",
        "Link liên kết đến tài liệu chính theo văn bản"
    ]
    assert sheet_data[0] == expected_header


def test_no_labels_in_col_d(sheet_data):
    for idx, row in enumerate(sheet_data[1:], start=2):
        d_val = row[3] if len(row) > 3 else ""
        assert "Người xử lí" not in d_val, f"Row {idx} still contains 'Người xử lí'"
        assert "Người theo dõi" not in d_val, f"Row {idx} still contains 'Người theo dõi'"
        assert "Đơn vị nhận" not in d_val, f"Row {idx} still contains 'Đơn vị nhận'"


def test_multiline_separation(sheet_data):
    # D2 must have 21 lines, E2 must have 14 lines
    row2 = sheet_data[1]
    d2 = row2[3]
    e2 = row2[4]

    d2_lines = d2.split("\n")
    e2_lines = e2.split("\n")

    assert len(d2_lines) == 21, f"D2 expected 21 lines, got {len(d2_lines)}"
    assert d2_lines[0] == "Tổ công tác (Tổ công tác)"
    assert d2_lines[1] == "Chủ tịch UBND tỉnh (Phạm Anh Tuấn)"
    assert d2_lines[2] == "Phó Chủ tịch Thường trực UBND tỉnh (Nguyễn Tuấn Thanh)"

    assert len(e2_lines) == 14, f"E2 expected 14 lines, got {len(e2_lines)}"
    assert e2_lines[0] == "Trung tâm Phục vụ hành chính công tỉnh Gia Lai"
    assert e2_lines[1] == "UBND phường Quy Nhơn - Tỉnh Gia Lai"


def test_edge_cases(sheet_data):
    # STT 194 (row 195)
    row_194 = sheet_data[194]
    assert row_194[0] == "194"
    assert row_194[1] == "12916/UBND-XDCT"
    assert len(row_194[3].split("\n")) == 2
    assert (row_194[4] if len(row_194) > 4 else "") == ""

    # STT 229 (row 230)
    row_229 = sheet_data[229]
    assert row_229[0] == "229"
    assert row_229[1] == "12881/UBND-KGVX"
    assert len(row_229[3].split("\n")) == 2
    assert (row_229[4] if len(row_229) > 4 else "") == ""

    # STT 500 (row 501)
    row_500 = sheet_data[500]
    assert row_500[0] == "500"
    assert row_500[1] == "12610/UBND-NNMT"
    assert len(row_500[3].split("\n")) == 5
    assert len(row_500[4].split("\n")) == 2
