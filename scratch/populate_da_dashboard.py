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

def populate_dashboard():
    token = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get sheetId for SHEET_TITLE
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}?fields=sheets.properties"
    res = requests.get(meta_url, headers=headers).json()
    sheet_id = None
    for s in res.get("sheets", []):
        if s["properties"]["title"] == SHEET_TITLE:
            sheet_id = s["properties"]["sheetId"]
            break
    assert sheet_id is not None, f"Sheet '{SHEET_TITLE}' not found!"
    print(f"Target Sheet ID: {sheet_id}")

    # 2. Prepare grid values (Rows 1 to 42, Cols A to G)
    # 1-indexed rows, 0-indexed in Python
    grid = [["" for _ in range(7)] for _ in range(43)] # Rows 0 to 42

    # Row 2 (Index 1)
    grid[1][1] = "BÁO CÁO THỐNG KÊ & ĐÁNH GIÁ CHẤT LƯỢNG MÔ HÌNH (DATA ANALYST REPORT)"
    
    # Row 3 (Index 2)
    grid[2][1] = "Đối chiếu kết quả Nơi nhận 2 (AI Lookup) với Kết quả đích thực tế trên tập 500 văn bản VPUB (Test 4)"
    
    # Row 4 (Index 3)
    grid[3][1] = "📌 Lưu ý nghiệp vụ: Toàn bộ 53 trường hợp 'Ngoại lệ' được loại trừ khỏi tính toán theo yêu cầu (do bản chất ngoại lệ không thể đối soát đích xác). Dữ liệu được tính trên số lượng thực thể duy nhất (unique entities) của từng văn bản."

    # Row 6-8: KPI Summary Cards (Indices 5, 6, 7)
    grid[5][1] = "TỔNG VĂN BẢN"
    grid[6][1] = "=D17"
    grid[7][1] = "100% Tập mẫu Test 4"

    grid[5][2] = "VĂN BẢN ĐÚNG 100%"
    grid[6][2] = "=D12"
    grid[7][2] = "45.80% (Khớp hoàn toàn)"

    grid[5][3] = "VĂN BẢN SAI LỆCH"
    grid[6][3] = "=D13"
    grid[7][3] = "54.20% (Có dư hoặc thiếu)"

    grid[5][4] = "PRECISION (CHÍNH XÁC)"
    grid[6][4] = "=D32"
    grid[7][4] = "15,358 / 16,760 đơn vị"

    grid[5][5] = "RECALL (BAO PHỦ)"
    grid[6][5] = "=D33"
    grid[7][5] = "15,358 / 15,978 đơn vị"

    grid[5][6] = "F1-SCORE (CÂN BẰNG)"
    grid[6][6] = "=D34"
    grid[7][6] = "Điểm điều hòa P & R"

    # Row 10: Section 1 Header (Index 9)
    grid[9][1] = "I. THỐNG KÊ ĐÁNH GIÁ CẤP ĐỘ VĂN BẢN (DOCUMENT-LEVEL PERFORMANCE)"

    # Row 11: Table 1 Headers (Index 10)
    grid[10][1] = "Phân loại Văn bản (Document Category)"
    grid[10][2] = "Chi tiết Phân nhóm"
    grid[10][3] = "Số lượng (VB)"
    grid[10][4] = "Tỷ lệ (%)"
    grid[10][5] = "Tiêu chí xác định"
    grid[10][6] = "Nhận xét & Ý nghĩa nghiệp vụ của Data Analyst"

    # Row 12: Đúng 100% (Index 11)
    grid[11][1] = "1. Văn bản ĐÚNG (Khớp 100%)"
    grid[11][2] = "Không sai lệch"
    grid[11][3] = 229
    grid[11][4] = "=D12/$D$17"
    grid[11][5] = "Dư = 0 VÀ Thiếu = 0"
    grid[11][6] = "Kết quả Nơi nhận 2 trùng khớp 100% với Kết quả đích thực tế. Văn bản đạt chuẩn ban hành ngay, không cần con người hiệu chỉnh."

    # Row 13: Sai lệch tổng (Index 12)
    grid[12][1] = "2. Văn bản SAI LỆCH (Tổng số)"
    grid[12][2] = "Có phát sinh lỗi"
    grid[12][3] = 271
    grid[12][4] = "=D13/$D$17"
    grid[12][5] = "Dư > 0 HOẶC Thiếu > 0"
    grid[12][6] = "Văn bản có ít nhất một sai sót (gán thừa hoặc bỏ sót đơn vị). Cần rà soát hoặc hiệu chỉnh thủ công trước khi gửi."

    # Row 14: Chỉ Dư (Index 13)
    grid[13][1] = "   2.1. Sai lệch: Chỉ Dư đơn vị"
    grid[13][2] = "Dư đơn vị (FP)"
    grid[13][3] = 47
    grid[13][4] = "=D14/$D$17"
    grid[13][5] = "Dư > 0 VÀ Thiếu = 0"
    grid[13][6] = "Hệ thống gán thừa đơn vị (thường là cấp Lãnh đạo hoặc Sở ngành mở rộng), nhưng đã bao phủ đủ 100% các đơn vị đích thực tế."

    # Row 15: Chỉ Thiếu (Index 14)
    grid[14][1] = "   2.2. Sai lệch: Chỉ Thiếu đơn vị"
    grid[14][2] = "Thiếu đơn vị (FN)"
    grid[14][3] = 133
    grid[14][4] = "=D15/$D$17"
    grid[14][5] = "Dư = 0 VÀ Thiếu > 0"
    grid[14][6] = "Không thừa đơn vị nào nhưng bị sót đơn vị đích thực tế (chiếm tỷ trọng cao nhất trong các dạng sai: 26.60% tổng mẫu)."

    # Row 16: Vừa Dư vừa Thiếu (Index 15)
    grid[15][1] = "   2.3. Sai lệch: Vừa Dư vừa Thiếu"
    grid[15][2] = "Hỗn hợp (FP & FN)"
    grid[15][3] = 91
    grid[15][4] = "=D16/$D$17"
    grid[15][5] = "Dư > 0 VÀ Thiếu > 0"
    grid[15][6] = "Xuất hiện đồng thời cả đơn vị gán thừa lẫn đơn vị bỏ sót trong cùng một văn bản (chiếm 18.20% tổng mẫu)."

    # Row 17: Tổng cộng (Index 16)
    grid[16][1] = "TỔNG CỘNG TẬP MẪU KIỂM THỬ"
    grid[16][2] = "Toàn bộ tập Test 4"
    grid[16][3] = "=D12+D13"
    grid[16][4] = "=SUM(E12:E13)"
    grid[16][5] = "500 văn bản thực tế"
    grid[16][6] = "Tổng số 500 văn bản hành chính công VPUB tỉnh Gia Lai được nghiệm thu đối soát toàn diện."

    # Row 18: Tần suất có Dư (Index 17)
    grid[17][1] = "📊 Tần suất xuất hiện yếu tố Dư"
    grid[17][2] = "Có xuất hiện Dư"
    grid[17][3] = "=D14+D16"
    grid[17][4] = "=D18/$D$17"
    grid[17][5] = "Dư >= 1 đơn vị"
    grid[17][6] = "Tổng cộng 138 văn bản (27.60%) có phát sinh đơn vị thừa. Gồm nhóm 'Chỉ Dư' (47) + 'Vừa Dư vừa Thiếu' (91)."

    # Row 19: Tần suất có Thiếu (Index 18)
    grid[18][1] = "📊 Tần suất xuất hiện yếu tố Thiếu"
    grid[18][2] = "Có xuất hiện Thiếu"
    grid[18][3] = "=D15+D16"
    grid[18][4] = "=D19/$D$17"
    grid[18][5] = "Thiếu >= 1 đơn vị"
    grid[18][6] = "Tổng cộng 224 văn bản (44.80%) bị sót đơn vị. Gồm nhóm 'Chỉ Thiếu' (133) + 'Vừa Dư vừa Thiếu' (91). Đây là nhóm lỗi chủ yếu."

    # Row 21: Section 2 Header (Index 20)
    grid[20][1] = "II. THỐNG KÊ ĐÁNH GIÁ CẤP ĐỘ THỰC THỂ ĐƠN VỊ (ENTITY-LEVEL PERFORMANCE)"

    # Row 22: Table 2 Headers (Index 21)
    grid[21][1] = "Thành phần Thực thể (Entity Type)"
    grid[21][2] = "Ký hiệu Machine Learning"
    grid[21][3] = "Số lượng (Đơn vị)"
    grid[21][4] = "Tỷ trọng tập cơ sở (%)"
    grid[21][5] = "Cơ sở đối soát"
    grid[21][6] = "Định nghĩa kỹ thuật & Ý nghĩa nghiệp vụ"

    # Row 23: Khớp TP (Index 22)
    grid[22][1] = "1. Thực thể Khớp (Chính xác)"
    grid[22][2] = "True Positive (TP)"
    grid[22][3] = 15358
    grid[22][4] = "=D23/$D$26"
    grid[22][5] = "Nơi nhận 2 ∩ Đích"
    grid[22][6] = "Đơn vị xuất hiện ở cả Nơi nhận 2 và Kết quả đích. Hệ thống nhận diện chuẩn xác 15,358 lượt thực thể (chiếm 91.63% kết quả dự đoán)."

    # Row 24: Dư FP (Index 23)
    grid[23][1] = "2. Thực thể Dư (Gán thừa)"
    grid[23][2] = "False Positive (FP)"
    grid[23][3] = 1402
    grid[23][4] = "=D24/$D$26"
    grid[23][5] = "Nơi nhận 2 \\ Đích"
    grid[23][6] = "Đơn vị xuất hiện ở Nơi nhận 2 nhưng KHÔNG có trong Kết quả đích. Chiếm 8.37% tổng số đơn vị Nơi nhận 2 sinh ra."

    # Row 25: Thiếu FN (Index 24)
    grid[24][1] = "3. Thực thể Thiếu (Bỏ sót)"
    grid[24][2] = "False Negative (FN)"
    grid[24][3] = 620
    grid[24][4] = "=D25/$D$27"
    grid[24][5] = "Đích \\ Nơi nhận 2"
    grid[24][6] = "Đơn vị CÓ trong Kết quả đích thực tế nhưng Nơi nhận 2 KHÔNG nhận diện được. Chiếm 3.88% tổng số đơn vị đích thực tế."

    # Row 26: Tổng Nơi nhận 2 (Index 25)
    grid[25][1] = "TỔNG THỰC THỂ NƠI NHẬN 2"
    grid[25][2] = "Predicted Positives"
    grid[25][3] = "=D23+D24"
    grid[25][4] = "=SUM(E23:E24)"
    grid[25][5] = "TP + FP"
    grid[25][6] = "Tổng quy mô thực thể do hệ thống AI bóc tách & lookup (đã deduplicate theo từng văn bản)."

    # Row 27: Tổng Đích thực tế (Index 26)
    grid[26][1] = "TỔNG THỰC THỂ KẾT QUẢ ĐÍCH"
    grid[26][2] = "Actual Positives"
    grid[26][3] = "=D23+D25"
    grid[26][4] = 1.0
    grid[26][5] = "TP + FN"
    grid[26][6] = "Tổng quy mô thực thể chuẩn thực tế (Ground Truth) cần gửi của 500 văn bản kiểm thử."

    # Row 28: Ngoại lệ (Index 27)
    grid[27][1] = "📌 Thực thể Ngoại lệ (Loại trừ)"
    grid[27][2] = "Excluded Entities"
    grid[27][3] = 53
    grid[27][4] = "-"
    grid[27][5] = "Không tính vào chỉ số"
    grid[27][6] = "Các đơn vị mơ hồ, không thể đối soát đích xác theo yêu cầu nghiệp vụ. Hoàn toàn được tách biệt khỏi các phép tính trên."

    # Row 30: Section 3 Header (Index 29)
    grid[29][1] = "III. BẢNG TỔNG HỢP CHỈ SỐ HIỆU NĂNG MÔ HÌNH (MODEL PERFORMANCE SCORECARD)"

    # Row 31: Table 3 Headers (Index 30)
    grid[30][1] = "Chỉ số đo lường (Evaluation Metric)"
    grid[30][2] = "Ký hiệu"
    grid[30][3] = "Giá trị thực tế (%)"
    grid[30][4] = "Công thức toán học"
    grid[30][5] = "Thang đánh giá chuẩn"
    grid[30][6] = "Phân tích & Diễn giải ý nghĩa của Data Analyst"

    # Row 32: Precision (Index 31)
    grid[31][1] = "Precision (Độ chính xác nơi nhận)"
    grid[31][2] = "P"
    grid[31][3] = "=D23/D26"
    grid[31][4] = "TP / (TP + FP) = 15,358 / 16,760"
    grid[31][5] = "Xuất sắc (> 90%)"
    grid[31][6] = "Khi hệ thống đề xuất 100 đơn vị gửi đi, có ~92 đơn vị là hoàn toàn chính xác. Tỷ lệ nhiễu gán thừa (False Alarm) chỉ 8.37%."

    # Row 33: Recall (Index 32)
    grid[32][1] = "Recall (Độ bao phủ / Độ nhạy)"
    grid[32][2] = "R"
    grid[32][3] = "=D23/D27"
    grid[32][4] = "TP / (TP + FN) = 15,358 / 15,978"
    grid[32][5] = "Rất cao (> 95%)"
    grid[32][6] = "Hệ thống tìm ra và bao phủ được tới 96.12% tổng số đơn vị thực tế cần gửi. Tỷ lệ bỏ sót chỉ 3.88%."

    # Row 34: F1-Score (Index 33)
    grid[33][1] = "F1-Score (Độ chuẩn xác cân bằng)"
    grid[33][2] = "F1"
    grid[33][3] = "=2*(D32*D33)/(D32+D33)"
    grid[33][4] = "2 * (P * R) / (P + R)"
    grid[33][5] = "Rất cao (> 90%)"
    grid[33][6] = "Thước đo hài hòa thể hiện mô hình đạt chất lượng tổng thể rất vững chắc giữa độ chính xác và độ bao phủ."

    # Row 35: Jaccard (Index 34)
    grid[34][1] = "Jaccard Similarity (Độ tương đồng)"
    grid[34][2] = "IoU"
    grid[34][3] = "=D23/(D23+D24+D25)"
    grid[34][4] = "TP / (TP + FP + FN) = 15,358 / 17,380"
    grid[34][5] = "Tốt (> 85%)"
    grid[34][6] = "Đo lường mức độ trùng khớp trực tiếp giữa tập kết quả đề xuất Nơi nhận 2 và tập chuẩn thực tế."

    # Row 36: Doc Accuracy (Index 35)
    grid[35][1] = "Document Accuracy (Chuẩn tuyệt đối cấp VB)"
    grid[35][2] = "Acc_doc"
    grid[35][3] = "=D12/D17"
    grid[35][4] = "VB Đúng / Tổng VB = 229 / 500"
    grid[35][5] = "Khá (40% - 50%)"
    grid[35][6] = "Tỷ lệ văn bản đạt độ hoàn hảo tuyệt đối 100% (không thừa 1 đơn vị nào VÀ không thiếu 1 đơn vị nào)."

    # Row 38: Section 4 Header (Index 37)
    grid[37][1] = "IV. GHI CHÚ CHUYÊN SÂU & ĐỀ XUẤT TỐI ƯU CỦA DATA ANALYST (INSIGHTS & ACTION ITEMS)"

    # Row 39: Note 1 (Index 38)
    grid[38][1] = "1. Nguyên tắc xử lý 53 Ngoại lệ"
    grid[38][2] = "Theo yêu cầu bài toán, toàn bộ 53 đơn vị thuộc diện 'Ngoại lệ' (được đánh dấu màu đỏ trong bảng gốc) không được đưa vào tính toán tỉ lệ chính xác và độ bao phủ.\nLý do nghiệp vụ: Các đơn vị ngoại lệ này xuất phát từ việc văn bản gốc chỉ ghi chung chung, viết tắt không thể tra cứu thực thể cụ thể (ví dụ: các tổ chức chưa có mã định danh, nhóm làm việc tạm thời), do đó không có cơ sở xác định đúng/sai một cách khách quan."

    # Row 40: Note 2 (Index 39)
    grid[39][1] = "2. Nghịch lý giữa Cấp Văn bản & Cấp Thực thể"
    grid[39][2] = "Có sự khác biệt rõ rệt giữa độ chính xác cấp Văn bản (45.80%) và cấp Thực thể (Precision 91.63%, Recall 96.12%):\n- Mỗi văn bản trung bình chứa ~32 đơn vị nhận. Để đạt 'Đúng' ở cấp văn bản, mô hình bắt buộc phải đạt độ chính xác 100% (không dư và không thiếu dù chỉ 1 đơn vị).\n- Trong thực tế, chỉ cần 1 lỗi nhỏ (ví dụ: dư 1 phòng ban hoặc thiếu 1 chuyên viên), văn bản đó đã bị xếp vào nhóm 'Sai'.\n- Do đó, tỷ lệ 45.80% văn bản đúng tuyệt đối là kết quả rất tích cực đối với bài toán gán nhãn đa nhãn (multi-label), đồng thời F1 đạt 93.82% khẳng định năng lực cốt lõi của mô hình là rất tốt."

    # Row 41: Note 3 (Index 40)
    grid[40][1] = "3. Khuyến nghị cải tiến kỹ thuật (Actionable Insights)"
    grid[40][2] = "① Tập trung xử lý lỗi Thiếu (44.80% VB bị thiếu): Đây là nhóm lỗi lớn nhất. Cần xây dựng rule mở rộng tự động cho các chức danh nội bộ VPUB (Lãnh đạo UBND, các Phó Ban, chuyên viên phụ trách) khi gặp cụm từ gom nhóm như 'CVP, PCVP' hoặc 'Chủ tịch và các PCT'.\n② Tối ưu giảm lỗi Dư (27.60% VB bị dư): Cần siết chặt logic trích xuất khi văn bản đề cập đến các xã/phường, tránh trường hợp văn bản chỉ gửi đích danh 1 vài xã nhưng hệ thống lại suy diễn gửi toàn bộ các xã trong huyện."

    # 3. Write data to sheet
    print("Writing grid values to Google Sheets...")
    val_body = {"values": grid}
    val_url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'{SHEET_TITLE}'!A1:G43?valueInputOption=USER_ENTERED"
    val_r = requests.put(val_url, headers=headers, json=val_body)
    assert val_r.status_code == 200, f"Write values failed: {val_r.text}"
    print(f"Values written: {val_r.json().get('updatedCells')} cells updated.")

    return sheet_id

if __name__ == "__main__":
    populate_dashboard()
