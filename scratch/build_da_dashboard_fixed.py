import json
import requests
from pathlib import Path

TOKEN_PATH = Path(r"C:\Users\trant\.gemini\antigravity\plugin_data\gsheets\token.json")
SPREADSHEET_ID = "1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s"
SHEET_TITLE = "Thống kê Đánh giá (DA)"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return {"red": round(r, 3), "green": round(g, 3), "blue": round(b, 3)}

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

def build_da_dashboard():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check existing sheets
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    res = requests.get(meta_url, headers=headers).json()
    sheets = res.get("sheets", [])
    
    existing_sheet_id = None
    for s in sheets:
        if s["properties"]["title"] == SHEET_TITLE:
            existing_sheet_id = s["properties"]["sheetId"]
            break
            
    if existing_sheet_id is not None:
        print(f"Sheet '{SHEET_TITLE}' already exists with ID {existing_sheet_id}. Deleting to recreate clean...")
        del_body = {"requests": [{"deleteSheet": {"sheetId": existing_sheet_id}}]}
        del_r = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
            headers=headers,
            json=del_body
        )
        assert del_r.status_code == 200, f"Failed to delete existing sheet: {del_r.text}"
        print("Deleted existing sheet.")

    # 2. Add sheet at index 0
    print(f"Creating new sheet '{SHEET_TITLE}' at index 0...")
    add_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": SHEET_TITLE,
                        "index": 0,
                        "gridProperties": {
                            "rowCount": 50,
                            "columnCount": 9,
                            "frozenRowCount": 0,
                            "hideGridlines": False
                        },
                        "tabColor": hex_to_rgb("#1A365D")
                    }
                }
            }
        ]
    }
    add_r = requests.post(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate",
        headers=headers,
        json=add_body
    )
    assert add_r.status_code == 200, f"Failed to add sheet: {add_r.text}"
    new_sheet_id = add_r.json()["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"Created sheet successfully with sheetId: {new_sheet_id}")

    # 3. Build Grid Data (Rows 1 to 46, Cols A to G)
    grid = [["" for _ in range(7)] for _ in range(46)]

    # Row 2 (Index 1) - Title
    grid[1][1] = "BÁO CÁO THỐNG KÊ & ĐÁNH GIÁ CHẤT LƯỢNG MÔ HÌNH (DATA ANALYST DASHBOARD)"

    # Row 3 (Index 2) - Subtitle
    grid[2][1] = "Đối soát kết quả Nơi nhận 2 (AI Lookup) với Kết quả đích thực tế trên tập 500 văn bản VPUB tỉnh Gia Lai (Test 4)"

    # Row 4 (Index 3) - Scope & Business Policy Note
    grid[3][1] = "📌 Nguyên tắc nghiệp vụ: Loại trừ hoàn toàn 53 đơn vị 'Ngoại lệ' theo yêu cầu (do bản chất ngoại lệ không thể đối soát đích xác). Số liệu tính trên thực thể duy nhất (unique entities) của từng văn bản."

    # TIER 1 KPI CARDS (Document-level) - Rows 6 to 8 (Indices 5, 6, 7)
    # Card 1 (B6:C8) - Tổng VB
    grid[5][1] = "TỔNG VĂN BẢN KHẢO SÁT"
    grid[6][1] = "=D21"
    grid[7][1] = "100% Tập mẫu nghiệm thu Test 4"

    # Card 2 (D6:E8) - VB Đúng
    grid[5][3] = "VĂN BẢN ĐÚNG 100%"
    grid[6][3] = "=D16"
    grid[7][3] = "45.80% (Khớp tuyệt đối, không dư/thiếu)"

    # Card 3 (F6:G8) - VB Sai lệch
    grid[5][5] = "VĂN BẢN SAI LỆCH (DƯ / THIẾU)"
    grid[6][5] = "=D17"
    grid[7][5] = "54.20% | Có Dư: 138 VB | Có Thiếu: 224 VB"

    # TIER 2 KPI CARDS (Entity-level NLP Performance) - Rows 10 to 12 (Indices 9, 10, 11)
    # Card 4 (B10:C12) - Precision
    grid[9][1] = "PRECISION (ĐỘ CHÍNH XÁC NƠI NHẬN)"
    grid[10][1] = "=D36"
    grid[11][1] = "15,358 / 16,760 thực thể AI sinh ra"

    # Card 5 (D10:E12) - Recall
    grid[9][3] = "RECALL (ĐỘ BAO PHỦ ĐÍCH THỰC TẾ)"
    grid[10][3] = "=D37"
    grid[11][3] = "15,358 / 15,978 thực thể đích cần gửi"

    # Card 6 (F10:G12) - F1-Score
    grid[9][5] = "F1-SCORE (ĐỘ CHUẨN XÁC CÂN BẰNG)"
    grid[10][5] = "=D38"
    grid[11][5] = "Điểm điều hòa P & R | Jaccard IoU: 88.37%"

    # SECTION I: BẢNG 1 - THỐNG KÊ CẤP ĐỘ VĂN BẢN (DOCUMENT-LEVEL)
    # Row 14 (Index 13) - Section 1 Header
    grid[13][1] = "I. THỐNG KÊ ĐÁNH GIÁ CẤP ĐỘ VĂN BẢN (DOCUMENT-LEVEL PERFORMANCE)"

    # Row 15 (Index 14) - Table 1 Headers
    grid[14][1] = "Phân loại Văn bản (Document Category)"
    grid[14][2] = "Chi tiết Phân nhóm"
    grid[14][3] = "Số lượng (VB)"
    grid[14][4] = "Tỷ lệ (%)"
    grid[14][5] = "Tiêu chí xác định"
    grid[14][6] = "Nhận xét & Ý nghĩa nghiệp vụ Data Analyst"

    # Row 16 (Index 15) - 1. Đúng 100%
    grid[15][1] = "1. Văn bản ĐÚNG (Khớp 100%)"
    grid[15][2] = "Khớp hoàn toàn"
    grid[15][3] = 229
    grid[15][4] = "=D16/$D$21"
    grid[15][5] = "Dư = 0 VÀ Thiếu = 0"
    grid[15][6] = "Kết quả Nơi nhận 2 trùng khớp 100% với Kết quả đích thực tế. Văn bản đạt chuẩn ban hành ngay, không cần hiệu chỉnh."

    # Row 17 (Index 16) - 2. Sai lệch (Tổng số)
    grid[16][1] = "2. Văn bản SAI LỆCH (Tổng số)"
    grid[16][2] = "Có phát sinh lỗi"
    grid[16][3] = "=D18+D19+D20"
    grid[16][4] = "=D17/$D$21"
    grid[16][5] = "Dư > 0 HOẶC Thiếu > 0"
    grid[16][6] = "Văn bản có ít nhất một sai sót (gán thừa hoặc bỏ sót đơn vị). Cần rà soát hoặc hiệu chỉnh thủ công trước khi gửi."

    # Row 18 (Index 17) - 2.1 Chỉ Dư
    grid[17][1] = "   2.1. Sai lệch: Chỉ Dư đơn vị"
    grid[17][2] = "Dư đơn vị (FP)"
    grid[17][3] = 47
    grid[17][4] = "=D18/$D$21"
    grid[17][5] = "Dư > 0 VÀ Thiếu = 0"
    grid[17][6] = "Gán thừa đơn vị (thường là cấp Lãnh đạo hoặc Sở ngành mở rộng), nhưng đã bao phủ đủ 100% các đơn vị đích thực tế."

    # Row 19 (Index 18) - 2.2 Chỉ Thiếu
    grid[18][1] = "   2.2. Sai lệch: Chỉ Thiếu đơn vị"
    grid[18][2] = "Thiếu đơn vị (FN)"
    grid[18][3] = 133
    grid[18][4] = "=D19/$D$21"
    grid[18][5] = "Dư = 0 VÀ Thiếu > 0"
    grid[18][6] = "Không thừa đơn vị nào nhưng bị sót đơn vị đích thực tế (chiếm tỷ trọng cao nhất trong các dạng sai: 26.60% tổng mẫu)."

    # Row 20 (Index 19) - 2.3 Vừa Dư vừa Thiếu
    grid[19][1] = "   2.3. Sai lệch: Vừa Dư vừa Thiếu"
    grid[19][2] = "Hỗn hợp (FP & FN)"
    grid[19][3] = 91
    grid[19][4] = "=D20/$D$21"
    grid[19][5] = "Dư > 0 VÀ Thiếu > 0"
    grid[19][6] = "Xuất hiện đồng thời cả đơn vị gán thừa lẫn đơn vị bỏ sót trong cùng một văn bản (chiếm 18.20% tổng mẫu)."

    # Row 21 (Index 20) - Tổng cộng tập mẫu
    grid[20][1] = "TỔNG CỘNG TẬP MẪU KIỂM THỬ"
    grid[20][2] = "Toàn bộ tập Test 4"
    grid[20][3] = "=D16+D17"
    grid[20][4] = "=SUM(E16:E17)"
    grid[20][5] = "500 văn bản thực tế"
    grid[20][6] = "Tổng số 500 văn bản hành chính công VPUB tỉnh Gia Lai được nghiệm thu đối soát toàn diện."

    # Row 22 (Index 21) - Tần suất Dư
    grid[21][1] = "📊 Tần suất xuất hiện yếu tố Dư"
    grid[21][2] = "Có xuất hiện Dư"
    grid[21][3] = "=D18+D20"
    grid[21][4] = "=D22/$D$21"
    grid[21][5] = "Dư >= 1 đơn vị"
    grid[21][6] = "Tổng cộng 138 văn bản (27.60%) có phát sinh đơn vị thừa. Gồm nhóm 'Chỉ Dư' (47) + 'Vừa Dư vừa Thiếu' (91)."

    # Row 23 (Index 22) - Tần suất Thiếu
    grid[22][1] = "📊 Tần suất xuất hiện yếu tố Thiếu"
    grid[22][2] = "Có xuất hiện Thiếu"
    grid[22][3] = "=D19+D20"
    grid[22][4] = "=D23/$D$21"
    grid[22][5] = "Thiếu >= 1 đơn vị"
    grid[22][6] = "Tổng cộng 224 văn bản (44.80%) bị sót đơn vị. Gồm nhóm 'Chỉ Thiếu' (133) + 'Vừa Dư vừa Thiếu' (91). Đây là nhóm lỗi chủ yếu."

    # SECTION II: BẢNG 2 - THỐNG KÊ CẤP ĐỘ THỰC THỂ (ENTITY-LEVEL)
    # Row 25 (Index 24) - Section 2 Header
    grid[24][1] = "II. THỐNG KÊ ĐÁNH GIÁ CẤP ĐỘ THỰC THỂ ĐƠN VỊ (ENTITY-LEVEL PERFORMANCE)"

    # Row 26 (Index 25) - Table 2 Headers
    grid[25][1] = "Thành phần Thực thể (Entity Type)"
    grid[25][2] = "Ký hiệu Machine Learning"
    grid[25][3] = "Số lượng (Đơn vị)"
    grid[25][4] = "Tỷ trọng trên Nơi nhận 2 (%)"
    grid[25][5] = "Tỷ trọng trên Đích thực tế (%)"
    grid[25][6] = "Cơ sở đối soát & Ý nghĩa Data Analyst"

    # Row 27 (Index 26) - Khớp TP
    grid[26][1] = "1. Thực thể Khớp (Chính xác)"
    grid[26][2] = "True Positive (TP)"
    grid[26][3] = 15358
    grid[26][4] = "=D27/$D$30"
    grid[26][5] = "=D27/$D$31"
    grid[26][6] = "Đơn vị xuất hiện ở cả Nơi nhận 2 và Kết quả đích. Hệ thống nhận diện chuẩn xác 15,358 lượt thực thể."

    # Row 28 (Index 27) - Dư FP
    grid[27][1] = "2. Thực thể Dư (Gán thừa)"
    grid[27][2] = "False Positive (FP)"
    grid[27][3] = 1402
    grid[27][4] = "=D28/$D$30"
    grid[27][5] = "-"
    grid[27][6] = "Đơn vị xuất hiện ở Nơi nhận 2 nhưng KHÔNG có trong Kết quả đích. Chiếm 8.37% tổng số đơn vị Nơi nhận 2 sinh ra."

    # Row 29 (Index 28) - Thiếu FN
    grid[28][1] = "3. Thực thể Thiếu (Bỏ sót)"
    grid[28][2] = "False Negative (FN)"
    grid[28][3] = 620
    grid[28][4] = "-"
    grid[28][5] = "=D29/$D$31"
    grid[28][6] = "Đơn vị CÓ trong Kết quả đích nhưng Nơi nhận 2 KHÔNG nhận diện được. Chiếm 3.88% tổng số đơn vị đích thực tế."

    # Row 30 (Index 29) - Tổng Nơi nhận 2
    grid[29][1] = "🎯 TỔNG THỰC THỂ NƠI NHẬN 2"
    grid[29][2] = "Predicted Positives (TP + FP)"
    grid[29][3] = "=D27+D28"
    grid[29][4] = "=D30/$D$30"
    grid[29][5] = "=D30/$D$31"
    grid[29][6] = "Tổng quy mô thực thể do hệ thống AI trích xuất & lookup (đã deduplicate theo từng văn bản)."

    # Row 31 (Index 30) - Tổng Đích thực tế
    grid[30][1] = "🎯 TỔNG THỰC THỂ KẾT QUẢ ĐÍCH"
    grid[30][2] = "Actual Positives (TP + FN)"
    grid[30][3] = "=D27+D29"
    grid[30][4] = "=D31/$D$30"
    grid[30][5] = "=D31/$D$31"
    grid[30][6] = "Tổng quy mô thực thể chuẩn thực tế (Ground Truth) cần gửi của 500 văn bản kiểm thử."

    # Row 32 (Index 31) - Ngoại lệ
    grid[31][1] = "📌 Thực thể Ngoại lệ (Loại trừ)"
    grid[31][2] = "Excluded Entities"
    grid[31][3] = 53
    grid[31][4] = "Loại trừ"
    grid[31][5] = "Loại trừ"
    grid[31][6] = "Các đơn vị mơ hồ, không thể đối soát đích xác theo yêu cầu nghiệp vụ. Hoàn toàn được tách biệt khỏi các phép tính trên."

    # SECTION III: BẢNG 3 - TỔNG HỢP HIỆU NĂNG MÔ HÌNH (SCORECARD)
    # Row 34 (Index 33) - Section 3 Header
    grid[33][1] = "III. BẢNG TỔNG HỢP CHỈ SỐ HIỆU NĂNG MÔ HÌNH (MODEL PERFORMANCE SCORECARD)"

    # Row 35 (Index 34) - Table 3 Headers
    grid[34][1] = "Chỉ số đo lường (Evaluation Metric)"
    grid[34][2] = "Ký hiệu"
    grid[34][3] = "Giá trị thực tế (%)"
    grid[34][4] = "Công thức toán học"
    grid[34][5] = "Thang đánh giá chuẩn"
    grid[34][6] = "Phân tích & Diễn giải ý nghĩa của Data Analyst"

    # Row 36 (Index 35) - Precision
    grid[35][1] = "Precision (Độ chính xác nơi nhận)"
    grid[35][2] = "P"
    grid[35][3] = "=D27/D30"
    grid[35][4] = "TP / (TP + FP) = 15,358 / 16,760"
    grid[35][5] = "Xuất sắc (> 90%)"
    grid[35][6] = "Khi hệ thống đề xuất 100 đơn vị gửi đi, có ~92 đơn vị là hoàn toàn chính xác. Tỷ lệ nhiễu gán thừa (False Alarm) chỉ 8.37%."

    # Row 37 (Index 36) - Recall
    grid[36][1] = "Recall (Độ bao phủ / Độ nhạy)"
    grid[36][2] = "R"
    grid[36][3] = "=D27/D31"
    grid[36][4] = "TP / (TP + FN) = 15,358 / 15,978"
    grid[36][5] = "Rất cao (> 95%)"
    grid[36][6] = "Hệ thống tìm ra và bao phủ được tới 96.12% tổng số đơn vị thực tế cần gửi. Tỷ lệ bỏ sót chỉ 3.88%."

    # Row 38 (Index 37) - F1-Score
    grid[37][1] = "F1-Score (Độ chuẩn xác cân bằng)"
    grid[37][2] = "F1"
    grid[37][3] = "=2*(D36*D37)/(D36+D37)"
    grid[37][4] = "2 * (P * R) / (P + R)"
    grid[37][5] = "Rất cao (> 90%)"
    grid[37][6] = "Thước đo hài hòa thể hiện mô hình đạt chất lượng tổng thể rất vững chắc giữa độ chính xác và độ bao phủ."

    # Row 39 (Index 38) - Jaccard Similarity
    grid[38][1] = "Jaccard Similarity (Độ tương đồng)"
    grid[38][2] = "IoU"
    grid[38][3] = "=D27/(D27+D28+D29)"
    grid[38][4] = "TP / (TP + FP + FN) = 15,358 / 17,380"
    grid[38][5] = "Tốt (> 85%)"
    grid[38][6] = "Đo lường mức độ trùng khớp trực tiếp giữa tập kết quả đề xuất Nơi nhận 2 và tập chuẩn thực tế."

    # Row 40 (Index 39) - Document Accuracy
    grid[39][1] = "Document Accuracy (Chuẩn tuyệt đối cấp VB)"
    grid[39][2] = "Acc_doc"
    grid[39][3] = "=D16/D21"
    grid[39][4] = "VB Đúng / Tổng VB = 229 / 500"
    grid[39][5] = "Khá (40% - 50%)"
    grid[39][6] = "Tỷ lệ văn bản đạt độ hoàn hảo tuyệt đối 100% (không thừa 1 đơn vị nào VÀ không thiếu 1 đơn vị nào)."

    # SECTION IV: GHI CHÚ CHUYÊN SÂU & ĐỀ XUẤT CỦA DATA ANALYST
    # Row 42 (Index 41) - Section 4 Header
    grid[41][1] = "IV. GHI CHÚ CHUYÊN SÂU & ĐỀ XUẤT TỐI ƯU CỦA DATA ANALYST (INSIGHTS & ACTION ITEMS)"

    # Row 43 (Index 42) - Note 1
    grid[42][1] = "1. Nguyên tắc xử lý 53 Ngoại lệ"
    grid[42][2] = "Theo yêu cầu bài toán, toàn bộ 53 đơn vị thuộc diện 'Ngoại lệ' (được đánh dấu màu đỏ trong bảng gốc) không được đưa vào tính toán tỉ lệ chính xác và độ bao phủ.\nLý do nghiệp vụ: Các đơn vị ngoại lệ này xuất phát từ việc văn bản gốc chỉ ghi chung chung, viết tắt không thể tra cứu thực thể cụ thể (ví dụ: các tổ chức chưa có mã định danh, nhóm làm việc tạm thời), do đó không có cơ sở xác định đúng/sai một cách khách quan."

    # Row 44 (Index 43) - Note 2
    grid[43][1] = "2. Nghịch lý giữa Cấp Văn bản & Cấp Thực thể"
    grid[43][2] = "Có sự khác biệt rõ rệt giữa độ chính xác cấp Văn bản (45.80%) và cấp Thực thể (Precision 91.63%, Recall 96.12%):\n- Mỗi văn bản trung bình chứa ~32 đơn vị nhận. Để đạt 'Đúng' ở cấp văn bản, mô hình bắt buộc phải đạt độ chính xác 100% (không dư và không thiếu dù chỉ 1 đơn vị).\n- Trong thực tế, chỉ cần 1 lỗi nhỏ (ví dụ: dư 1 phòng ban hoặc thiếu 1 chuyên viên), văn bản đó đã bị xếp vào nhóm 'Sai'.\n- Do đó, tỷ lệ 45.80% văn bản đúng tuyệt đối là kết quả rất tích cực đối với bài toán gán nhãn đa nhãn (multi-label), đồng thời F1 đạt 93.82% khẳng định năng lực cốt lõi của mô hình là rất tốt."

    # Row 45 (Index 44) - Note 3
    grid[44][1] = "3. Khuyến nghị cải tiến kỹ thuật (Actionable Insights)"
    grid[44][2] = "① Tập trung xử lý lỗi Thiếu (44.80% VB bị thiếu): Đây là nhóm lỗi lớn nhất. Cần xây dựng rule mở rộng tự động cho các chức danh nội bộ VPUB (Lãnh đạo UBND, các Phó Ban, chuyên viên phụ trách) khi gặp cụm từ gom nhóm như 'CVP, PCVP' hoặc 'Chủ tịch và các PCT'.\n② Tối ưu giảm lỗi Dư (27.60% VB bị dư): Cần siết chặt logic trích xuất khi văn bản đề cập đến các xã/phường, tránh trường hợp văn bản chỉ gửi đích danh 1 vài xã nhưng hệ thống lại suy diễn gửi toàn bộ các xã trong huyện."

    # Write data to Google Sheets
    print("Writing grid values to Google Sheets...")
    val_body = {"values": grid}
    val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{SHEET_TITLE}'!A1:G46?valueInputOption=USER_ENTERED"
    val_r = requests.put(val_url, headers=headers, json=val_body)
    assert val_r.status_code == 200, f"Write values failed: {val_r.text}"
    print(f"Values written: {val_r.json().get('updatedCells')} cells updated.")

    # 4. Apply Complete Professional Styling & Layout
    requests_list = []

    # Column Widths (Cols A to G)
    col_widths = [
        (0, 1, 24),   # A: Margin
        (1, 2, 240),  # B: Phân loại / Chỉ số
        (2, 3, 160),  # C: Ký hiệu / Phân nhóm
        (3, 4, 160),  # D: Số lượng (VB / Đơn vị)
        (4, 5, 180),  # E: Tỷ lệ (%) / % Nơi nhận 2
        (5, 6, 180),  # F: Tiêu chí / % Đích thực tế / Công thức
        (6, 7, 320),  # G: Nhận xét Data Analyst
    ]
    for start_c, end_c, width in col_widths:
        requests_list.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": new_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_c,
                    "endIndex": end_c
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize"
            }
        })

    # Row Heights
    row_heights = [
        (0, 1, 15),   # R1: Padding
        (1, 2, 44),   # R2: Title
        (2, 3, 28),   # R3: Subtitle
        (3, 4, 34),   # R4: Scope note
        (4, 5, 14),   # R5: Spacing
        (5, 6, 28),   # R6: Card 1-3 Header
        (6, 7, 42),   # R7: Card 1-3 Value
        (7, 8, 28),   # R8: Card 1-3 Subtitle
        (8, 9, 12),   # R9: Spacing
        (9, 10, 28),  # R10: Card 4-6 Header
        (10, 11, 42), # R11: Card 4-6 Value
        (11, 12, 28), # R12: Card 4-6 Subtitle
        (12, 13, 16), # R13: Spacing
        (13, 14, 32), # R14: Sec 1 Header
        (14, 15, 30), # R15: Table 1 Header
        (15, 16, 38), # R16: VB Đúng
        (16, 17, 38), # R17: VB Sai tổng
        (17, 18, 38), # R18: Chỉ Dư
        (18, 19, 42), # R19: Chỉ Thiếu
        (19, 20, 38), # R20: Vừa Dư vừa Thiếu
        (20, 21, 34), # R21: Tổng cộng
        (21, 22, 36), # R22: Tần suất Dư
        (22, 23, 42), # R23: Tần suất Thiếu
        (23, 24, 16), # R24: Spacing
        (24, 25, 32), # R25: Sec 2 Header
        (25, 26, 30), # R26: Table 2 Header
        (26, 27, 38), # R27: Khớp TP
        (27, 28, 38), # R28: Dư FP
        (28, 29, 38), # R29: Thiếu FN
        (29, 30, 34), # R30: Tổng Nơi nhận 2
        (30, 31, 34), # R31: Tổng Đích
        (31, 32, 38), # R32: Ngoại lệ
        (32, 33, 16), # R33: Spacing
        (33, 34, 32), # R34: Sec 3 Header
        (34, 35, 30), # R35: Table 3 Header
        (35, 36, 40), # R36: Precision
        (36, 37, 40), # R37: Recall
        (37, 38, 40), # R38: F1-Score
        (38, 39, 40), # R39: Jaccard
        (39, 40, 40), # R40: Doc Accuracy
        (40, 41, 16), # R41: Spacing
        (41, 42, 32), # R42: Sec 4 Header
        (42, 43, 75), # R43: Note 1
        (43, 44, 110),# R44: Note 2
        (44, 45, 105),# R45: Note 3
    ]
    for start_r, end_r, height in row_heights:
        requests_list.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": new_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_r,
                    "endIndex": end_r
                },
                "properties": {"pixelSize": height},
                "fields": "pixelSize"
            }
        })

    # Merges
    merges = [
        # Title block
        (1, 2, 1, 7),   # R2: B2:G2 (Title)
        (2, 3, 1, 7),   # R3: B3:G3 (Subtitle)
        (3, 4, 1, 7),   # R4: B4:G4 (Scope Note)
        # Tier 1 KPI Cards (Rows 6-8: indices 5-8)
        (5, 6, 1, 3),   # Card 1 Title (B6:C6)
        (6, 7, 1, 3),   # Card 1 Value (B7:C7)
        (7, 8, 1, 3),   # Card 1 Subtitle (B8:C8)
        (5, 6, 3, 5),   # Card 2 Title (D6:E6)
        (6, 7, 3, 5),   # Card 2 Value (D7:E7)
        (7, 8, 3, 5),   # Card 2 Subtitle (D8:E8)
        (5, 6, 5, 7),   # Card 3 Title (F6:G6)
        (6, 7, 5, 7),   # Card 3 Value (F7:G7)
        (7, 8, 5, 7),   # Card 3 Subtitle (F8:G8)
        # Tier 2 KPI Cards (Rows 10-12: indices 9-12)
        (9, 10, 1, 3),  # Card 4 Title (B10:C10)
        (10, 11, 1, 3), # Card 4 Value (B11:C11)
        (11, 12, 1, 3), # Card 4 Subtitle (B12:C12)
        (9, 10, 3, 5),  # Card 5 Title (D10:E10)
        (10, 11, 3, 5), # Card 5 Value (D11:E11)
        (11, 12, 3, 5), # Card 5 Subtitle (D12:E12)
        (9, 10, 5, 7),  # Card 6 Title (F10:G10)
        (10, 11, 5, 7), # Card 6 Value (F11:G11)
        (11, 12, 5, 7), # Card 6 Subtitle (F12:G12)
        # Section Headers
        (13, 14, 1, 7), # R14: B14:G14 (Sec 1)
        (24, 25, 1, 7), # R25: B25:G25 (Sec 2)
        (33, 34, 1, 7), # R34: B34:G34 (Sec 3)
        (41, 42, 1, 7), # R42: B42:G42 (Sec 4)
        # Section 4 Notes
        (42, 43, 2, 7), # R43: C43:G43 (Note 1)
        (43, 44, 2, 7), # R44: C44:G44 (Note 2)
        (44, 45, 2, 7), # R45: C45:G45 (Note 3)
    ]
    for sr, er, sc, ec in merges:
        requests_list.append({
            "mergeCells": {
                "range": {
                    "sheetId": new_sheet_id,
                    "startRowIndex": sr,
                    "endRowIndex": er,
                    "startColumnIndex": sc,
                    "endColumnIndex": ec
                },
                "mergeType": "MERGE_ALL"
            }
        })

    # Base Font & Alignment for entire grid (B2:G45)
    requests_list.append({
        "repeatCell": {
            "range": {
                "sheetId": new_sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 45,
                "startColumnIndex": 1,
                "endColumnIndex": 7
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 10,
                        "foregroundColor": hex_to_rgb("#2D3748")
                    },
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.textFormat.fontFamily,userEnteredFormat.textFormat.fontSize,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # Title Styling (R2: B2:G2)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#1A365D"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 15,
                        "bold": True,
                        "foregroundColor": hex_to_rgb("#FFFFFF")
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
        }
    })

    # Subtitle Styling (R3: B3:G3)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#2B6CB0"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 10,
                        "italic": True,
                        "foregroundColor": hex_to_rgb("#E2E8F0")
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
        }
    })

    # Scope Banner Styling (R4: B4:G4)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {
                        "fontFamily": "Segoe UI",
                        "fontSize": 9,
                        "italic": True,
                        "foregroundColor": hex_to_rgb("#2D3748")
                    },
                    "horizontalAlignment": "LEFT",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # KPI Summary Cards Styling
    # Cards layout: 6 cards arranged in 2 tiers (Rows 6-8 and Rows 10-12)
    cards_specs = [
        # (startRow, endRow, startCol, endCol, bgHex, valColorHex, labelColorHex, borderHex, numType)
        # Tier 1: Document level
        (5, 8, 1, 3, "#F7FAFC", "#1A365D", "#4A5568", "#CBD5E0", "NUMBER"),   # Card 1: Tổng VB (B6:C8)
        (5, 8, 3, 5, "#E6F4EA", "#137333", "#137333", "#A8DAB5", "NUMBER"),   # Card 2: VB Đúng (D6:E8)
        (5, 8, 5, 7, "#FCE8E6", "#C5221F", "#C5221F", "#F5C2C7", "NUMBER"),   # Card 3: VB Sai (F6:G8)
        # Tier 2: Entity / ML level
        (9, 12, 1, 3, "#EBF8FF", "#2B6CB0", "#1A365D", "#BEE3F8", "PERCENT"), # Card 4: Precision (B10:C12)
        (9, 12, 3, 5, "#EBF8FF", "#2B6CB0", "#1A365D", "#BEE3F8", "PERCENT"), # Card 5: Recall (D10:E12)
        (9, 12, 5, 7, "#FAF5FF", "#6B46C1", "#553C9A", "#E9D8FD", "PERCENT"), # Card 6: F1-Score (F10:G12)
    ]

    for sr, er, sc, ec, bg_hex, val_color_hex, label_color_hex, border_hex, num_type in cards_specs:
        # Border
        requests_list.append({
            "updateBorders": {
                "range": {
                    "sheetId": new_sheet_id,
                    "startRowIndex": sr,
                    "endRowIndex": er,
                    "startColumnIndex": sc,
                    "endColumnIndex": ec
                },
                "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb(border_hex)},
                "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb(border_hex)},
                "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb(border_hex)},
                "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb(border_hex)},
                "innerHorizontal": {"style": "NONE"},
                "innerVertical": {"style": "NONE"},
            }
        })
        # Background for entire card
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": sr, "endRowIndex": er, "startColumnIndex": sc, "endColumnIndex": ec},
                "cell": {"userEnteredFormat": {"backgroundColor": hex_to_rgb(bg_hex)}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })
        # Card Header (Row sr)
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": sr, "endRowIndex": sr + 1, "startColumnIndex": sc, "endColumnIndex": ec},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 10,
                            "bold": True,
                            "foregroundColor": hex_to_rgb(label_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "BOTTOM"
                    }
                },
                "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })
        # Card Value (Row sr + 1)
        num_fmt = {"type": "PERCENT", "pattern": "0.00%"} if num_type == "PERCENT" else {"type": "NUMBER", "pattern": "#,##0"}
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": sr + 1, "endRowIndex": sr + 2, "startColumnIndex": sc, "endColumnIndex": ec},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 20,
                            "bold": True,
                            "foregroundColor": hex_to_rgb(val_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "numberFormat": num_fmt
                    }
                },
                "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.numberFormat"
            }
        })
        # Card Subtitle (Row sr + 2)
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": sr + 2, "endRowIndex": sr + 3, "startColumnIndex": sc, "endColumnIndex": ec},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 9,
                            "italic": True,
                            "foregroundColor": hex_to_rgb(label_color_hex)
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "TOP"
                    }
                },
                "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # Section Headers (R14, R25, R34, R42: indices 13, 24, 33, 41)
    for r_idx, title_bg in [(13, "#2B6CB0"), (24, "#2B6CB0"), (33, "#1A365D"), (41, "#2D3748")]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 1, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb(title_bg),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 11,
                            "bold": True,
                            "foregroundColor": hex_to_rgb("#FFFFFF")
                        },
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # Table Column Headers (R15, R26, R35: indices 14, 25, 34)
    for r_idx in [14, 25, 34]:
        requests_list.append({
            "repeatCell": {
                "range": {"sheetId": new_sheet_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 1, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": hex_to_rgb("#EDF2F7"),
                        "textFormat": {
                            "fontFamily": "Segoe UI",
                            "fontSize": 10,
                            "bold": True,
                            "foregroundColor": hex_to_rgb("#1A202C")
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment"
            }
        })

    # Alignments for Tables:
    # Col B: Left
    # Col C: Center
    # Col D: Center
    # Col E: Center
    # Col F: Center
    # Col G: Left (Wrap)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 14, "endRowIndex": 41, "startColumnIndex": 2, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 14, "endRowIndex": 41, "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 14, "endRowIndex": 41, "startColumnIndex": 6, "endColumnIndex": 7},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })

    # Number Formats:
    # Table 1 Col D (Counts: R16 to R23)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 15, "endRowIndex": 23, "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    # Table 1 Col E (Percents: R16 to R23)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 15, "endRowIndex": 23, "startColumnIndex": 4, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    # Table 2 Col D (Counts: R27 to R32)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 26, "endRowIndex": 32, "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    # Table 2 Col E & F (Percents: R27 to R31)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 26, "endRowIndex": 31, "startColumnIndex": 4, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    # Table 3 Col D (Percents: R36 to R40)
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 35, "endRowIndex": 40, "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"bold": True, "fontSize": 11},
                    "numberFormat": {"type": "PERCENT", "pattern": "0.00%"}
                }
            },
            "fields": "userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.fontSize,userEnteredFormat.numberFormat"
        }
    })

    # Row Highlights:
    # Table 1:
    # R16: VB Đúng -> Soft Green
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 15, "endRowIndex": 16, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F0FFF4"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#22543D")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 15, "endRowIndex": 16, "startColumnIndex": 1, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"
        }
    })
    # R17: VB Sai tổng -> Soft Red, Bold
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 16, "endRowIndex": 17, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FFF5F5"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#742A2A"), "bold": True}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R21: Tổng cộng tập mẫu -> Soft Gray, Bold All, Double Bottom Border
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R22 & R23: Tần suất Dư & Thiếu -> Soft Slate Gray, Italic
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 21, "endRowIndex": 23, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"italic": True, "foregroundColor": hex_to_rgb("#4A5568")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Table 2:
    # R27: TP Khớp -> Light Green
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 26, "endRowIndex": 27, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F0FFF4"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#22543D")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R28: FP Dư -> Light Amber
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 27, "endRowIndex": 28, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FEFCBF"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#744210")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    # R29: FN Thiếu -> Light Red
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 28, "endRowIndex": 29, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FFF5F5"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#C53030")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.foregroundColor"
        }
    })
    # R30 & R31: Totals -> Soft Gray, Bold
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 29, "endRowIndex": 31, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })
    # R32: Ngoại lệ -> Italic Gray
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 31, "endRowIndex": 32, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"italic": True, "foregroundColor": hex_to_rgb("#718096")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Table 3:
    # R38: F1-Score Highlight -> Light Purple
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 37, "endRowIndex": 38, "startColumnIndex": 1, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#FAF5FF"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#6B46C1")}
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
        }
    })

    # Section 4 Notes:
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 42, "endRowIndex": 45, "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#EDF2F7"),
                    "textFormat": {"bold": True, "foregroundColor": hex_to_rgb("#1A202C")},
                    "verticalAlignment": "TOP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment"
        }
    })
    requests_list.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 42, "endRowIndex": 45, "startColumnIndex": 2, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": hex_to_rgb("#F7FAFC"),
                    "textFormat": {"foregroundColor": hex_to_rgb("#2D3748"), "fontSize": 10},
                    "verticalAlignment": "TOP",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy"
        }
    })

    # Table Borders:
    # Table 1 Borders (R15 to R23: indices 14 to 23, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 14, "endRowIndex": 23, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })
    # Table 1 Total Row Double Bottom Border (R21, index 20)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 20, "endRowIndex": 21, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#718096")},
            "bottom": {"style": "DOUBLE", "color": hex_to_rgb("#1A202C")},
        }
    })

    # Table 2 Borders (R26 to R32: indices 25 to 32, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 25, "endRowIndex": 32, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })
    # Table 2 Ground Truth Total Double Bottom Border (R31, index 30)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 30, "endRowIndex": 31, "startColumnIndex": 1, "endColumnIndex": 7},
            "bottom": {"style": "DOUBLE", "color": hex_to_rgb("#1A202C")},
        }
    })

    # Table 3 Borders (R35 to R40: indices 34 to 40, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 34, "endRowIndex": 40, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })

    # Section 4 Notes Borders (R43 to R45: indices 42 to 45, cols 1 to 7)
    requests_list.append({
        "updateBorders": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 42, "endRowIndex": 45, "startColumnIndex": 1, "endColumnIndex": 7},
            "top": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "bottom": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "left": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "right": {"style": "SOLID_MEDIUM", "color": hex_to_rgb("#4A5568")},
            "innerHorizontal": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")},
            "innerVertical": {"style": "SOLID", "color": hex_to_rgb("#E2E8F0")}
        }
    })

    print(f"Sending batchUpdate with {len(requests_list)} formatting requests...")
    batch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}:batchUpdate"
    resp = requests.post(batch_url, headers=headers, json={"requests": requests_list})
    assert resp.status_code == 200, f"batchUpdate failed: {resp.text}"
    print("Formatting applied successfully!")
    return new_sheet_id

if __name__ == "__main__":
    build_da_dashboard()
