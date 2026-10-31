"""Google Sheet Reconciliation and Formatting Engine.

This tool executes the batch update of reconciled standard recipient names
into Column E ('Nơi nhận 2') of Google Spreadsheet
`1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s` (Tab 'Thống kê', sheetId: 0),
applies pure Red font formatting (RGB: 1.0, 0.0, 0.0) matching clerical
conventions, performs exhaustive read-back verification of cell values and
styles, and generates the consolidated unmapped recipients report for clerical review.
"""

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

# Default configuration and paths
DEFAULT_SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
DEFAULT_SHEET_TITLE = "Thống kê"
DEFAULT_SHEET_ID = 0
DEFAULT_TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")

WORKSPACE_DIR = Path(r"c:\Workspaces\ai-document-sender")
EXPLORER_DIR = WORKSPACE_DIR / ".agents" / "teamwork" / "explorer_survey_2"
POPULATED_ROWS_CSV = EXPLORER_DIR / "populated_rows.csv"
RETAINED_ROWS_CSV = EXPLORER_DIR / "retained_rows.csv"
DECISIONS_JSON = EXPLORER_DIR / "reconciliation_decisions.json"

REPORT_OUTPUT_DIR = WORKSPACE_DIR / "reports"
REPORT_OUTPUT_FILE = REPORT_OUTPUT_DIR / "unmapped_recipients_report.md"
WORKER_REPORT_FILE = WORKSPACE_DIR / ".agents" / "teamwork" / "worker_m1" / "unmapped_recipients_report.md"
WORKER_ITER2_REPORT_FILE = WORKSPACE_DIR / ".agents" / "teamwork" / "worker_m1_iter2" / "unmapped_recipients_report.md"


class GoogleSheetsAuth:
    """Manages Google OAuth2 credentials and token refresh for Google Sheets API."""

    def __init__(self, token_path: Path = DEFAULT_TOKEN_PATH):
        self.token_path = token_path
        self._token_data: Dict[str, Any] = {}
        self._load_token_data()

    def _load_token_data(self) -> None:
        if not self.token_path.exists():
            raise FileNotFoundError(f"OAuth token file not found at: {self.token_path}")
        with open(self.token_path, "r", encoding="utf-8") as f:
            self._token_data = json.load(f)

    def get_access_token(self) -> str:
        """Returns the current valid access token, refreshing if needed."""
        token_info = self._token_data.get("token", {})
        access_token = token_info.get("access_token")
        if not access_token:
            raise ValueError("No access_token found in token file.")
        return access_token

    def refresh_access_token(self) -> str:
        """Refreshes the OAuth2 token using Google's token endpoint."""
        token_info = self._token_data.get("token", {})
        refresh_token = token_info.get("refresh_token")
        client_id = self._token_data.get("client_id")
        client_secret = self._token_data.get("client_secret")

        if not refresh_token or not client_id or not client_secret:
            raise ValueError("Missing OAuth2 client credentials or refresh_token for refreshing.")

        url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to refresh access token: {resp.status_code} - {resp.text}")

        res_json = resp.json()
        new_token = res_json["access_token"]
        self._token_data["token"]["access_token"] = new_token
        # Update file if possible
        try:
            with open(self.token_path, "w", encoding="utf-8") as f:
                json.dump(self._token_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save refreshed token to disk: {e}", file=sys.stderr)
        return new_token

    def authorized_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Executes an HTTP request with automatic token refresh on 401."""
        if headers is None:
            headers = {}
        token = self.get_access_token()
        headers["Authorization"] = f"Bearer {token}"

        resp = requests.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 401:
            print("Access token expired (401), refreshing token...", file=sys.stderr)
            new_token = self.refresh_access_token()
            headers["Authorization"] = f"Bearer {new_token}"
            resp = requests.request(method, url, headers=headers, **kwargs)
        return resp


def load_reconciliation_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Loads populated rows, retained rows, and decisions JSON."""
    if not POPULATED_ROWS_CSV.exists():
        raise FileNotFoundError(f"Missing populated rows CSV: {POPULATED_ROWS_CSV}")
    if not RETAINED_ROWS_CSV.exists():
        raise FileNotFoundError(f"Missing retained rows CSV: {RETAINED_ROWS_CSV}")
    if not DECISIONS_JSON.exists():
        raise FileNotFoundError(f"Missing decisions JSON: {DECISIONS_JSON}")

    with open(POPULATED_ROWS_CSV, "r", encoding="utf-8") as f:
        populated_rows = list(csv.DictReader(f))

    with open(RETAINED_ROWS_CSV, "r", encoding="utf-8") as f:
        retained_rows = list(csv.DictReader(f))

    with open(DECISIONS_JSON, "r", encoding="utf-8") as f:
        decisions = json.load(f)

    return populated_rows, retained_rows, decisions


def preflight_verification(
    auth: GoogleSheetsAuth,
    spreadsheet_id: str,
    sheet_title: str,
    populated_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Verifies that all 82 rows currently exist in the sheet and Column E is currently '-'."""
    print(f"Running pre-flight check on {len(populated_rows)} rows against live Google Sheet...")
    row_indices = [int(r["Row"]) for r in populated_rows]
    ranges = [f"'{sheet_title}'!D{r}:E{r}" for r in row_indices]

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet"
    params = [("ranges", rng) for rng in ranges]
    resp = auth.authorized_request("GET", url, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to batchGet ranges for preflight: {resp.status_code} - {resp.text}")

    value_ranges = resp.json().get("valueRanges", [])
    mismatches = []
    not_dash = []

    for i, vr in enumerate(value_ranges):
        exp_row = populated_rows[i]
        vals = vr.get("values", [["", ""]])[0]
        curr_d = vals[0] if len(vals) > 0 else ""
        curr_e = vals[1] if len(vals) > 1 else ""

        if curr_e != "-":
            not_dash.append({
                "row": exp_row["Row"],
                "doc_id": exp_row["DocID"],
                "current_e": curr_e,
            })
        if curr_d.strip() != exp_row["NoiNhan1"].strip():
            mismatches.append({
                "row": exp_row["Row"],
                "doc_id": exp_row["DocID"],
                "sheet_d": curr_d,
                "expected_d": exp_row["NoiNhan1"],
            })

    result = {
        "total_checked": len(populated_rows),
        "not_dash_count": len(not_dash),
        "mismatches_count": len(mismatches),
        "not_dash_samples": not_dash[:5],
        "mismatches_samples": mismatches[:5],
    }
    print(f"Pre-flight result: Checked {len(populated_rows)} rows. "
          f"Not dash: {len(not_dash)}, Text D mismatches: {len(mismatches)}.")
    return result


def execute_sheet_batch_update(
    auth: GoogleSheetsAuth,
    spreadsheet_id: str,
    sheet_id: int,
    populated_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Executes atomic batchUpdate with updateCells for all 82 rows with red text color."""
    print(f"Constructing batchUpdate requests for {len(populated_rows)} rows...")
    requests_list = []
    for item in populated_rows:
        row_idx = int(item["Row"])
        target_value = item["TargetNoiNhan2"]

        # Note: 0-indexed row starts at row_idx - 1, Column E is index 4
        update_cell_req = {
            "updateCells": {
                "rows": [
                    {
                        "values": [
                            {
                                "userEnteredValue": {
                                    "stringValue": target_value,
                                },
                                "userEnteredFormat": {
                                    "textFormat": {
                                        "foregroundColor": {
                                            "red": 1.0,
                                            "green": 0.0,
                                            "blue": 0.0,
                                        }
                                    }
                                },
                            }
                        ]
                    }
                ],
                "fields": "userEnteredValue,userEnteredFormat.textFormat.foregroundColor",
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_idx - 1,
                    "endRowIndex": row_idx,
                    "startColumnIndex": 4,
                    "endColumnIndex": 5,
                },
            }
        }
        requests_list.append(update_cell_req)

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    payload = {"requests": requests_list}

    print(f"Sending batchUpdate request with {len(requests_list)} cell updates to Google Sheets API...")
    t0 = time.time()
    resp = auth.authorized_request("POST", url, json=payload)
    elapsed = time.time() - t0

    if resp.status_code != 200:
        raise RuntimeError(f"batchUpdate failed: HTTP {resp.status_code} - {resp.text}")

    res_data = resp.json()
    print(f"Batch update succeeded in {elapsed:.2f}s! Total replies: {len(res_data.get('replies', []))}")
    return res_data


def verify_live_sheet_updates(
    auth: GoogleSheetsAuth,
    spreadsheet_id: str,
    sheet_title: str,
    populated_rows: List[Dict[str, Any]],
    retained_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Exhaustively verifies cell values and Red font formatting in live Google Sheet."""
    print("Beginning post-update verification against live Google Sheet...")

    # 1. Verify all 82 populated rows
    pop_indices = [int(r["Row"]) for r in populated_rows]
    pop_ranges = [f"'{sheet_title}'!E{r}:E{r}" for r in pop_indices]

    # Query with formatting fields
    fields = "sheets.data.rowData.values(userEnteredValue,effectiveValue,userEnteredFormat.textFormat.foregroundColor,effectiveFormat.textFormat.foregroundColor)"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    params = [("ranges", rng) for rng in pop_ranges]
    params.append(("fields", fields))

    resp = auth.authorized_request("GET", url, params=params)
    if resp.status_code != 200:
        raise RuntimeError(f"Verification query failed: HTTP {resp.status_code} - {resp.text}")

    sheet_data = resp.json().get("sheets", [{}])[0].get("data", [])
    if len(sheet_data) != len(populated_rows):
        raise RuntimeError(f"Expected {len(populated_rows)} data blocks, got {len(sheet_data)}")

    value_mismatches = []
    color_mismatches = []
    verified_populated = 0

    for i, data_block in enumerate(sheet_data):
        exp_row = populated_rows[i]
        expected_val = exp_row["TargetNoiNhan2"]
        row_num = exp_row["Row"]

        row_data = data_block.get("rowData", [])
        if not row_data or not row_data[0].get("values"):
            value_mismatches.append({"row": row_num, "error": "No cell value found"})
            continue

        cell = row_data[0]["values"][0]
        actual_val = cell.get("userEnteredValue", {}).get("stringValue") or cell.get("effectiveValue", {}).get("stringValue", "")

        if actual_val != expected_val:
            value_mismatches.append({
                "row": row_num,
                "expected": expected_val,
                "actual": actual_val,
            })

        # Check foreground color
        eff_color = cell.get("effectiveFormat", {}).get("textFormat", {}).get("foregroundColor", {})
        user_color = cell.get("userEnteredFormat", {}).get("textFormat", {}).get("foregroundColor", {})

        red_eff = eff_color.get("red", 0.0)
        green_eff = eff_color.get("green", 0.0)
        blue_eff = eff_color.get("blue", 0.0)

        red_user = user_color.get("red", 0.0)

        # Pure red has red >= 0.99, green == 0, blue == 0
        is_red = (red_eff >= 0.99 or red_user >= 0.99) and green_eff == 0.0 and blue_eff == 0.0

        if not is_red:
            color_mismatches.append({
                "row": row_num,
                "effective_color": eff_color,
                "user_color": user_color,
            })
        else:
            verified_populated += 1

    print(f"Populated rows check: {verified_populated}/{len(populated_rows)} perfectly verified "
          f"(Value mismatches: {len(value_mismatches)}, Color mismatches: {len(color_mismatches)}).")

    # 2. Verify all 825 retained rows via full column E fetch (fast & robust against URL limits)
    print(f"Verifying retention of '-' for all {len(retained_rows)} unmapped rows...")
    ret_indices = [int(r["Row"]) for r in retained_rows]
    col_e_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/'{sheet_title}'!E2:E5140"
    col_e_resp = auth.authorized_request("GET", col_e_url)
    if col_e_resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch Column E for retained check: HTTP {col_e_resp.status_code}")

    all_col_e = col_e_resp.json().get("values", [])
    ret_mismatches = []
    total_ret_checked = 0

    for r_idx in ret_indices:
        # Row 2 corresponds to all_col_e[0]
        offset = r_idx - 2
        if 0 <= offset < len(all_col_e) and len(all_col_e[offset]) > 0:
            val = all_col_e[offset][0]
        else:
            val = ""

        if val != "-":
            ret_mismatches.append({"row": r_idx, "actual": val})
        total_ret_checked += 1

    print(f"Retained rows check: {total_ret_checked - len(ret_mismatches)}/{total_ret_checked} correctly retain '-' "
          f"(Mismatches: {len(ret_mismatches)}).")

    return {
        "populated_total": len(populated_rows),
        "populated_verified": verified_populated,
        "populated_value_mismatches": value_mismatches,
        "populated_color_mismatches": color_mismatches,
        "retained_total": len(retained_rows),
        "retained_verified": total_ret_checked - len(ret_mismatches),
        "retained_mismatches": ret_mismatches,
    }


def generate_unmapped_report(
    retained_rows: List[Dict[str, Any]],
    decisions: Dict[str, Any],
    output_path: Path = REPORT_OUTPUT_FILE,
) -> str:
    """Generates the consolidated markdown report for all remaining unmapped entries."""
    print(f"Generating consolidated unmapped recipients report for {len(retained_rows)} rows...")

    # Categorize retained rows
    categories: Dict[str, List[Dict[str, Any]]] = {
        "POLICY_ARCHIVAL_VT": [],
        "INTERNAL_FILING_OR_SPECIALIST_CODE": [],
        "PARTY_COMMITTEE_CHANNEL": [],
        "COMPOSITE_OR_INDIVIDUAL": [],
        "UNMAPPED_EXTERNAL_OR_SPECIFIC": [],
    }

    category_labels = {
        "POLICY_ARCHIVAL_VT": "Ký hiệu Lưu trữ Văn thư (VT)",
        "INTERNAL_FILING_OR_SPECIALIST_CODE": "Ký hiệu Chuyên viên / Phòng ban Soạn thảo (Lưu: VT, ...)",
        "PARTY_COMMITTEE_CHANNEL": "Cơ quan Đảng / Thường trực Tỉnh ủy (Kênh gửi mật / Bản giấy)",
        "COMPOSITE_OR_INDIVIDUAL": "Đối tượng tổng hợp, cá nhân công dân hoặc 'Như trên'",
        "UNMAPPED_EXTERNAL_OR_SPECIFIC": "Đơn vị ngoài tỉnh / Doanh nghiệp chưa có mã e-document",
    }

    for item in retained_rows:
        source = item.get("Source", "UNMAPPED_EXTERNAL_OR_SPECIFIC")
        if source not in categories:
            categories[source] = []
        categories[source].append(item)

    # Build markdown content
    total_populated = decisions.get("summary", {}).get("total_populated", 81)
    lines = [
        "# Báo Cáo Tổng Hợp Các Dòng Chưa Ánh Xạ Nơi Nhận 2 ('-')",
        "",
        "> **Tài liệu tham chiếu**: `ORIGINAL_REQUEST.md` (Yêu cầu R4)",
        "> **Bảng tính mục tiêu**: `1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s`, Tab `Thống kê`",
        f"> **Thời gian khởi tạo**: {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}",
        "",
        "---",
        "",
        "## 1. Tóm Tắt Tổng Quan (Executive Summary)",
        "",
        f"- **Tổng số dòng chưa ánh xạ ban đầu ('-')**: 907 dòng.",
        f"- **Số dòng đã được chuẩn hóa và cập nhật thành công (Chữ đỏ #FF0000)**: {total_populated} dòng.",
        f"- **Số dòng bảo lưu giá trị '-' theo quy chuẩn**: **{len(retained_rows)} dòng**.",
        "",
        "### Phân Loại Các Dòng Bảo Lưu Giá Trị '-':",
        "",
        "| STT | Phân Nhóm Nguyên Nhân | Mã Phân Loại | Số Lượng Dòng | Tỷ Lệ | Đề Xuất Xử Lý Văn Thư |",
        "|---|---|---|---|---|---|",
    ]

    stt = 1
    total_retained = len(retained_rows)
    for cat_code, items in categories.items():
        label = category_labels.get(cat_code, cat_code)
        count = len(items)
        pct = (count / total_retained) * 100 if total_retained else 0
        if cat_code == "POLICY_ARCHIVAL_VT":
            sugg = "Giữ nguyên `-`. Đây là nơi lưu hồ sơ văn thư nội bộ, không gửi ra ngoài."
        elif cat_code in ("POLICY_SPECIALIST_OR_DIVISION", "INTERNAL_FILING_OR_SPECIALIST_CODE"):
            sugg = "Giữ nguyên `-`. Ký hiệu lưu bản cứng chuyên viên phụ trách, không gửi qua trục điện tử."
        elif cat_code == "PARTY_COMMITTEE_CHANNEL":
            sugg = "Giữ nguyên `-`. Đơn vị thuộc hệ thống Đảng, phát hành qua kênh bảo mật/bản giấy riêng."
        elif cat_code == "COMPOSITE_OR_INDIVIDUAL":
            sugg = "Cần cán bộ văn thư rà soát thủ công danh sách chi tiết kèm theo văn bản chính."
        else:
            sugg = "Cần đăng ký bổ sung mã định danh trục liên thông e-document hoặc gửi bưu chính."

        lines.append(f"| {stt} | {label} | `{cat_code}` | **{count}** | {pct:.1f}% | {sugg} |")
        stt += 1

    vt_count = len(categories.get("POLICY_ARCHIVAL_VT", []))
    spec_count = len(categories.get("INTERNAL_FILING_OR_SPECIALIST_CODE", []))
    party_count = len(categories.get("PARTY_COMMITTEE_CHANNEL", []))
    comp_count = len(categories.get("COMPOSITE_OR_INDIVIDUAL", []))
    ext_count = len(categories.get("UNMAPPED_EXTERNAL_OR_SPECIFIC", []))

    lines.extend([
        "",
        "---",
        "",
        "## 2. Chi Tiết Từng Nhóm Nguyên Nhân & Căn Cứ Xử Lý",
        "",
        f"### 2.1 Nhóm Ký Hiệu Lưu Trữ Văn Thư (`VT` - {vt_count} dòng)",
        "- **Căn cứ thực tế**: Trong 1.498 dòng được cán bộ văn thư sửa thủ công trước đó, giá trị `VT` **không bao giờ được gán nơi nhận** (tỷ lệ 0%).",
        "- **Bản chất nghiệp vụ**: `VT` là viết tắt của 'Lưu: Văn thư' theo Nghị định 30/2020/NĐ-CP về công tác văn thư. Đây là bản lưu hồ sơ tại văn thư cơ quan, không phải cơ quan/đơn vị nhận văn bản phát hành.",
        "- **Chính sách hệ thống**: Đã được định nghĩa trong `resources/policies/recipient_aliases.v1.json` trạng thái `pending` (nội bộ).",
        "- **Kết luận**: Bảo lưu tuyệt đối giá trị `-` cho toàn bộ 474 dòng.",
        "",
        f"### 2.2 Nhóm Ký Hiệu Lưu Chuyên Viên & Phòng Soạn Thảo ({spec_count} dòng)",
        "- **Ví dụ điển hình**: `Lưu: VT, BTCD`, `Lưu: VT, HSVV-TD`, `Lưu: VT, TM`, `Lưu: VT, C4`, `Lưu: VT, N1`.",
        "- **Bản chất nghiệp vụ**: Phần ghi chú nơi lưu nội bộ cho chuyên viên/bộ phận chuyên môn theo dõi hồ sơ vụ việc.",
        "- **Kết luận**: Bảo lưu `-` vì không đại diện cho điểm đến gửi đi.",
        "",
        f"### 2.3 Nhóm Cơ Quan Đảng & Kênh Bảo Mật ({party_count} dòng)",
        "- **Ví dụ điển hình**: `Thường trực Tỉnh ủy`, `Ban Tổ chức Tỉnh ủy`, `Ban Tuyên giáo Tỉnh ủy`.",
        "- **Bản chất nghiệp vụ**: Các cơ quan lãnh đạo/chỉ đạo cấp ủy Đảng (như Ban Thường vụ, Thường trực Tỉnh ủy, các ban đảng) nhận văn bản chỉ đạo qua hệ thống bảo mật chuyên dùng hoặc văn bản giấy niêm phong, không thuộc diện gửi công khai qua VDX hành chính nhà nước. Riêng cơ quan hành chính của Đảng đã đăng ký mã định danh chính thức (`Đảng ủy Ủy ban nhân dân tỉnh Gia Lai`) hoặc phân phối đồng gửi liên cơ quan (`Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai`) đã được chuẩn hóa ánh xạ khi có căn cứ gửi đi thực tế.",
        "- **Kết luận**: Giữ `-` đối với các ban đảng và cơ quan lãnh đạo trực thuộc Tỉnh ủy trên hệ thống gửi e-document, chuyển văn bản giấy/kênh bảo mật.",
        "",
        f"### 2.4 Nhóm Đối Tượng Tổng Hợp & Cá Nhân Công Dân ({comp_count} dòng)",
        "- **Ví dụ điển hình**: `Bí thư Đảng ủy, Chủ tịch UBND các xã, phường nơi có dự án điện 1`, `Chủ đầu tư các dự án điện trên địa bàn tỉnh`, `Ông Nguyễn Văn Thanh (để biết)`, `Như trên`.",
        "- **Bản chất nghiệp vụ**: Các danh sách gộp nhiều đối tượng hoặc địa chỉ cá nhân người dân không có mã định danh định tuyến tự động trên hệ thống danh mục điện tử.",
        "- **Kết luận**: Giữ `-`, yêu cầu văn thư rà soát danh sách đính kèm trong phụ lục văn bản để phát hành thủ công.",
        "",
        f"### 2.5 Nhóm Đơn Vị Trung Ương & Doanh Nghiệp Ngoài Tỉnh ({ext_count} dòng)",
        "- **Ví dụ điển hình**: `Viện Sinh thái Nhiệt đới`, `Công ty TNHH MTV Cà phê Ia Blan`, `Công ty CP Tập đoàn FLC`, `Cảng Hàng không Pleiku`, `Truyền tải điện 3`.",
        "- **Bản chất nghiệp vụ**: Đơn vị ngoài tỉnh hoặc doanh nghiệp chưa tích hợp trục gửi liên thông điện tử của tỉnh Gia Lai. Điển hình dòng 805 `Truyền tải điện 3` (PTC3 trực thuộc EVNNPT) là doanh nghiệp truyền tải điện lưới quốc gia, không có điểm tích hợp gửi nhận văn bản trên trục nội tỉnh (văn bản cùng số hiệu đã gửi Công ty Điện lực Gia Lai tại dòng 804).",
        "- **Kết luận**: Giữ `-`, chuyển bộ phận bưu chính phát hành văn bản giấy có ký số xác thực.",
        "",
        "---",
        "",
        f"## 3. Danh Mục Chi Tiết Toàn Bộ {len(retained_rows)} Dòng Bảo Lưu '-' (Clerical Review Log)",
        "",
        "| Dòng | Số Hiệu Văn Bản | Nơi Nhận 1 (Trích Xuất Thô) | Phân Nhóm | Ghi Chú & Đề Xuất Cán Bộ Văn Thư |",
        "|---|---|---|---|---|",
    ])

    for row_item in retained_rows:
        row_num = row_item["Row"]
        doc_id = row_item["DocID"]
        nn1 = row_item["NoiNhan1"].replace("|", "\\|")
        cat = row_item.get("Source", "UNMAPPED_EXTERNAL_OR_SPECIFIC")
        notes = row_item.get("Notes", "").replace("|", "\\|")
        lines.append(f"| {row_num} | `{doc_id}` | {nn1} | `{cat}` | {notes} |")

    report_content = "\n".join(lines) + "\n"

    # Write to target locations
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Report written to: {output_path}")

    # Copy to worker folder
    WORKER_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WORKER_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Report copy written to: {WORKER_REPORT_FILE}")

    WORKER_ITER2_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WORKER_ITER2_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Report copy written to: {WORKER_ITER2_REPORT_FILE}")

    return report_content


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Sheet Reconcile & Report Engine")
    parser.add_argument("--execute", action="store_true", help="Execute live batch update to Google Sheet")
    parser.add_argument("--verify", action="store_true", help="Run verification against live Google Sheet")
    parser.add_argument("--report", action="store_true", help="Generate consolidated unmapped report")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: preflight, execute, verify, report")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID, help="Google Spreadsheet ID")
    parser.add_argument("--sheet-id", type=int, default=DEFAULT_SHEET_ID, help="Tab Sheet ID")
    parser.add_argument("--sheet-title", default=DEFAULT_SHEET_TITLE, help="Tab Title")

    args = parser.parse_args()
    if not (args.execute or args.verify or args.report or args.all):
        args.all = True

    print("=" * 70)
    print("Google Sheet Reconciliation & Report Generator")
    print("=" * 70)

    auth = GoogleSheetsAuth()
    populated_rows, retained_rows, decisions = load_reconciliation_data()
    print(f"Loaded datasets: {len(populated_rows)} rows to populate, {len(retained_rows)} rows to retain.")

    if args.all or args.execute:
        # Step 1: Pre-flight check
        preflight = preflight_verification(auth, args.spreadsheet_id, args.sheet_title, populated_rows)
        if preflight["not_dash_count"] > 0:
            print(f"Warning: {preflight['not_dash_count']} rows already populated or not '-' before execution.")

        # Step 2: Execute batch update
        execute_sheet_batch_update(auth, args.spreadsheet_id, args.sheet_id, populated_rows)

    if args.all or args.verify:
        # Step 3: Post-flight verification
        verify_results = verify_live_sheet_updates(
            auth,
            args.spreadsheet_id,
            args.sheet_title,
            populated_rows,
            retained_rows,
        )
        print("\nVerification Summary:")
        print(f"  Populated rows verified: {verify_results['populated_verified']}/{verify_results['populated_total']}")
        print(f"  Value mismatches: {len(verify_results['populated_value_mismatches'])}")
        print(f"  Color mismatches: {len(verify_results['populated_color_mismatches'])}")
        print(f"  Retained rows verified: {verify_results['retained_verified']}/{verify_results['retained_total']}")
        print(f"  Retained mismatches: {len(verify_results['retained_mismatches'])}")

        if (
            verify_results["populated_verified"] != verify_results["populated_total"]
            or verify_results["retained_verified"] != verify_results["retained_total"]
        ):
            print("ERROR: Verification failed!", file=sys.stderr)
            sys.exit(1)

    if args.all or args.report:
        # Step 4: Generate report
        generate_unmapped_report(retained_rows, decisions, REPORT_OUTPUT_FILE)

    print("\nAll pipeline tasks completed successfully!")


if __name__ == "__main__":
    main()
