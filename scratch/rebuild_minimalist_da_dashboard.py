import json
import requests
from pathlib import Path

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_TITLE = "Thống kê Đánh giá (DA)"

def get_valid_token():
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data["token"]["access_token"]
    refresh_token = data["token"].get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    test_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=properties.title"
    r = requests.get(test_url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 401 and refresh_token and client_id and client_secret:
        rf = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if rf.status_code == 200:
            token = rf.json()["access_token"]
            data["token"]["access_token"] = token
            with open(TOKEN_PATH, "w", encoding="utf-8") as f_out:
                json.dump(data, f_out, indent=2)
    return token

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"red": round(r, 3), "green": round(g, 3), "blue": round(b, 3)}

def apply_minimalist_fixes():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch metadata
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?ranges='{SHEET_TITLE}'&fields=sheets(properties,merges,bandedRanges)"
    res = requests.get(meta_url, headers=headers).json()
    sheet = res["sheets"][0]
    sheet_id = sheet["properties"]["sheetId"]

    # 2. Update Grid Values
    grid = [["" for _ in range(5)] for _ in range(33)]

    # Row 2 (index 1): Sheet Title
    grid[1][1] = "BÁO CÁO THỐNG KÊ ĐÁNH GIÁ CHẤT LƯỢNG MÔ HÌNH"
    # Row 3 (index 2): Subtitle
    grid[2][1] = "Đối soát kết quả Nơi nhận 2 (AI Lookup) với Kết quả đích thực tế trên tập 500 văn bản VPUB tỉnh Gia Lai (Test 4)"

    # --- BẢNG 1: THỐNG KÊ CẤP VĂN BẢN ---
    # Row 5 (index 4): Section Title
    grid[4][1] = "BẢNG 1: THỐNG KÊ CẤP VĂN BẢN (500 VĂN BẢN)"

    # Row 6 (index 5): Table 1 Headers
    grid[5][1] = "Phân loại văn bản"
    grid[5][2] = "Số lượng (VB)"
    grid[5][3] = "Tỷ lệ (%)"
    grid[5][4] = "Tiêu chí xác định"

    # Row 7 (index 6): VB Đúng
    grid[6][1] = "Văn bản Đúng (100% khớp)"
    grid[6][2] = 229
    grid[6][3] = "=C7/$C$12"
    grid[6][4] = "Dư = 0 VÀ Thiếu = 0"

    # Row 8 (index 7): VB Sai
    grid[7][1] = "Văn bản Sai"
    grid[7][2] = "=C9+C10+C11"
    grid[7][3] = "=C8/$C$12"
    grid[7][4] = "Dư > 0 HOẶC Thiếu > 0"

    # Row 9 (index 8): Chỉ Dư
    grid[8][1] = "   - Chỉ Dư"
    grid[8][2] = 47
    grid[8][3] = "=C9/$C$12"
    grid[8][4] = "Dư > 0 VÀ Thiếu = 0"

    # Row 10 (index 9): Chỉ Thiếu
    grid[9][1] = "   - Chỉ Thiếu"
    grid[9][2] = 133
    grid[9][3] = "=C10/$C$12"
    grid[9][4] = "Dư = 0 VÀ Thiếu > 0"

    # Row 11 (index 10): Vừa Dư vừa Thiếu
    grid[10][1] = "   - Vừa Dư vừa Thiếu"
    grid[10][2] = 91
    grid[10][3] = "=C11/$C$12"
    grid[10][4] = "Dư > 0 VÀ Thiếu > 0"

    # Row 12 (index 11): Tổng cộng
    grid[11][1] = "Tổng cộng"
    grid[11][2] = "=C7+C8"
    grid[11][3] = "=C12/$C$12"
    grid[11][4] = "Toàn bộ 500 văn bản mẫu"

    # Row 13 (index 12): Tóm tắt Dư
    grid[12][1] = "Tổng VB có Dư (Tóm tắt)"
    grid[12][2] = "=C9+C11"
    grid[12][3] = "=C13/$C$12"
    grid[12][4] = "Gồm Chỉ Dư (47) + Vừa Dư vừa Thiếu (91)"

    # Row 14 (index 13): Tóm tắt Thiếu
    grid[13][1] = "Tổng VB có Thiếu (Tóm tắt)"
    grid[13][2] = "=C10+C11"
    grid[13][3] = "=C14/$C$12"
    grid[13][4] = "Gồm Chỉ Thiếu (133) + Vừa Dư vừa Thiếu (91)"

    # --- BẢNG 2: THỐNG KÊ CẤP THỰC THỂ ---
    # Row 16 (index 15): Section Title
    grid[15][1] = "BẢNG 2: THỐNG KÊ CẤP THỰC THỂ (UNIQUE ENTITIES)"

    # Row 17 (index 16): Table 2 Headers
    grid[16][1] = "Thành phần thực thể"
    grid[16][2] = "Số lượng (Thực thể)"
    grid[16][3] = "Tỷ lệ (%)"
    grid[16][4] = "Ghi chú / Ký hiệu Machine Learning"

    # Row 18 (index 17): Khớp
    grid[17][1] = "Khớp"
    grid[17][2] = 15358
    grid[17][3] = "=C18/$C$21"
    grid[17][4] = "True Positive (TP) - Khớp giữa Nơi nhận 2 & Đích thực tế"

    # Row 19 (index 18): Dư
    grid[18][1] = "Dư"
    grid[18][2] = 1402
    grid[18][3] = "=C19/$C$21"
    grid[18][4] = "False Positive (FP) - Gán thừa trong Nơi nhận 2"

    # Row 20 (index 19): Thiếu
    grid[19][1] = "Thiếu"
    grid[19][2] = 620
    grid[19][3] = "=C20/$C$22"
    grid[19][4] = "False Negative (FN) - Bỏ sót so với Đích thực tế"

    # Row 21 (index 20): Tổng Nơi nhận 2
    grid[20][1] = "Tổng Nơi nhận 2"
    grid[20][2] = "=C18+C19"
    grid[20][3] = "=C21/$C$21"
    grid[20][4] = "Tổng thực thể AI trích xuất & lookup (TP + FP = 100%)"

    # Row 22 (index 21): Tổng Đích thực tế
    grid[21][1] = "Tổng Đích thực tế"
    grid[21][2] = "=C18+C20"
    grid[21][3] = "=C22/$C$22"
    grid[21][4] = "Tổng thực thể chuẩn thực tế cần gửi (TP + FN = 100%)"

    # Row 23 (index 22): Note
    grid[22][1] = "* Ghi chú: Đã loại bỏ 53 ngoại lệ khỏi tính toán (theo quy tắc nghiệp vụ đối soát)."

    # --- BẢNG 3: TỶ LỆ CHÍNH XÁC ---
    # Row 25 (index 24): Section Title
    grid[24][1] = "BẢNG 3: TỶ LỆ CHÍNH XÁC (%)"

    # Row 26 (index 25): Table 3 Headers
    grid[25][1] = "Chỉ số đo lường"
    grid[25][2] = "Giá trị (%)"
    grid[25][3] = "Chi tiết số liệu"
    grid[25][4] = "Công thức toán học"

    # Row 27 (index 26): Precision
    grid[26][1] = "Precision (Độ chuẩn xác Nơi nhận 2)"
    grid[26][2] = "=C18/C21"
    grid[26][3] = "15,358 / 16,760"
    grid[26][4] = "TP / (TP + FP) = Khớp / Tổng Nơi nhận 2"

    # Row 28 (index 27): Recall
    grid[27][1] = "Recall (Độ bao phủ Đích thực tế)"
    grid[27][2] = "=C18/C22"
    grid[27][3] = "15,358 / 15,978"
    grid[27][4] = "TP / (TP + FN) = Khớp / Tổng Đích thực tế"

    # Row 29 (index 28): F1-Score
    grid[28][1] = "F1-Score"
    grid[28][2] = "=2*(C27*C28)/(C27+C28)"
    grid[28][3] = "2 * (P * R) / (P + R)"
    grid[28][4] = "Cân bằng giữa Precision (91.63%) & Recall (96.12%)"

    # Row 30 (index 29): Doc Accuracy
    grid[29][1] = "Độ chính xác cấp văn bản"
    grid[29][2] = "=C7/C12"
    grid[29][3] = "229 / 500"
    grid[29][4] = "VB Đúng 100% / Tổng số VB"

    # Row 31 (index 30): Jaccard
    grid[30][1] = "Độ tương đồng (Jaccard)"
    grid[30][2] = "=C18/(C18+C19+C20)"
    grid[30][3] = "15,358 / 17,380"
    grid[30][4] = "TP / (TP + FP + FN) = Khớp / (Khớp + Dư + Thiếu)"

    # Write Values
    val_body = {"values": grid}
    val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{SHEET_TITLE}'!A1:E33?valueInputOption=USER_ENTERED"
    val_r = requests.put(val_url, headers=headers, json=val_body)
    assert val_r.status_code == 200, f"Write values failed: {val_r.text}"
    print(f"Values updated: {val_r.json().get('updatedCells')} cells.")

    # 3. Formatting Requests
    fmt_reqs = []

    # Optimized Column Widths to prevent ANY text clipping
    col_widths = [
        (0, 1, 24),   # A: Margin
        (1, 2, 300),  # B: Phân loại / Chỉ số
        (2, 3, 175),  # C: Số lượng / Giá trị (generous room for 'Số lượng (Thực thể)')
        (3, 4, 160),  # D: Tỷ lệ (%) / Chi tiết
        (4, 5, 460),  # E: Tiêu chí / Công thức / Ghi chú (generous room for full explanations)
        (5, 6, 30),   # F: Margin
    ]
    for start_c, end_c, width in col_widths:
        fmt_reqs.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_c,
                    "endIndex": end_c
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize"
            }
        })

    # Border definitions
    border_outer = {"style": "SOLID", "width": 1, "color": hex_to_rgb("#BDC1C6")}
    border_inner_h = {"style": "SOLID", "width": 1, "color": hex_to_rgb("#E8EAED")}
    border_inner_v = {"style": "SOLID", "width": 1, "color": hex_to_rgb("#E8EAED")}
    border_header_bottom = {"style": "SOLID_MEDIUM", "width": 2, "color": hex_to_rgb("#BDC1C6")}
    border_total_top = {"style": "SOLID", "width": 1, "color": hex_to_rgb("#BDC1C6")}
    border_total_bottom = {"style": "SOLID_MEDIUM", "width": 2, "color": hex_to_rgb("#BDC1C6")}

    # Fix Table 1 Borders:
    # Header (R6: index 5)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_outer,
            "bottom": border_header_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerVertical": border_inner_v
        }
    })
    # Data rows (R7 to R11: indices 6 to 11)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 6, "endRowIndex": 11, "startColumnIndex": 1, "endColumnIndex": 5},
            "left": border_outer,
            "right": border_outer,
            "innerHorizontal": border_inner_h,
            "innerVertical": border_inner_v
        }
    })
    # Summary rows (R13 to R14: indices 12 to 14) FIRST
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 12, "endRowIndex": 14, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_total_bottom,  # medium top so the boundary below R12 is medium
            "bottom": border_outer,
            "left": border_outer,
            "right": border_outer,
            "innerHorizontal": border_inner_h,
            "innerVertical": border_inner_v
        }
    })
    # Total row (R12: index 11) - applied AFTER R13 so bottom border stays SOLID_MEDIUM
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 12, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_total_top,
            "bottom": border_total_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerVertical": border_inner_v
        }
    })

    # Fix Table 2 Borders:
    # Header (R17: index 16)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 16, "endRowIndex": 17, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_outer,
            "bottom": border_header_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerVertical": border_inner_v
        }
    })
    # Data rows (R18 to R20: indices 17 to 20)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 17, "endRowIndex": 20, "startColumnIndex": 1, "endColumnIndex": 5},
            "left": border_outer,
            "right": border_outer,
            "innerHorizontal": border_inner_h,
            "innerVertical": border_inner_v
        }
    })
    # Total rows (R21 to R22: indices 20 to 22)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 20, "endRowIndex": 22, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_total_top,
            "bottom": border_total_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerHorizontal": border_inner_h,
            "innerVertical": border_inner_v
        }
    })

    # Fix Table 3 Borders:
    # Header (R26: index 25)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 25, "endRowIndex": 26, "startColumnIndex": 1, "endColumnIndex": 5},
            "top": border_outer,
            "bottom": border_header_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerVertical": border_inner_v
        }
    })
    # Data rows (R27 to R31: indices 26 to 31)
    fmt_reqs.append({
        "updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 26, "endRowIndex": 31, "startColumnIndex": 1, "endColumnIndex": 5},
            "bottom": border_total_bottom,
            "left": border_outer,
            "right": border_outer,
            "innerHorizontal": border_inner_h,
            "innerVertical": border_inner_v
        }
    })

    # Apply batch update
    fmt_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
    fmt_r = requests.post(fmt_url, headers=headers, json={"requests": fmt_reqs})
    assert fmt_r.status_code == 200, f"Formatting update failed: {fmt_r.text}"
    print(f"Batch update succeeded with {len(fmt_reqs)} operations.")

if __name__ == "__main__":
    apply_minimalist_fixes()
