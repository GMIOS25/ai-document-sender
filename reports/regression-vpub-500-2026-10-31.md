# Hồi quy 500 văn bản VPUB — 31/10/2026

Đã chạy lại 500 PDF gốc qua extract_document và resolve_mentions hiện tại. Tab kết quả: **Thống kê 2**, Google Sheets gốc. SHA-256 được đối chiếu với ghi chú nguồn; không dùng kết quả gửi thực tế làm đầu vào resolver.

| Chỉ số | Trước | Sau |
|---|---:|---:|
| Identity được chọn, mỗi ID một lần trong từng văn bản | 2698 | 4500 |
| Dòng sửa đỏ có đủ đích trong danh sách cuối (1025 dòng đối chiếu được) | 2 | 1005 |
| Văn bản có lỗi HTTP OpenRouter | 480 | 478 |

Giữ được 2698/2698 identity cũ; 0 identity không còn được chọn. Trong các identity mới, 1800 khớp đích đã được văn thư sửa. Còn 1416 mentions chưa resolve, 500 văn bản cần rà soát và 0 văn bản có extraction_status complete.

Loại 77 dòng đỏ mâu thuẫn khỏi đánh giá; 477 dòng khác còn thiếu hoặc trùng identity trong danh bạ. Có 2 dòng đỏ đủ đích nhưng raw đã thay đổi hoặc không trích xuất lại được. Không xem ứng viên search là identity đã chọn.

Các số trên mô tả tập đã dùng để đối soát/học. Chúng không phải độ chính xác trên văn bản mới. Lỗi cloud và trích xuất partial được giữ nguyên trong kết quả; lượt hồi quy không thay đổi cấu hình model hay sửa backend giữa chừng.

Mốc cũ được chốt bằng recipient_id có trong ghi chú nguồn. Có 22 ô đen có nhãn nhưng thiếu ghi chú ID; chúng được lưu riêng để rà soát, không được suy ra thành identity backend cũ. Vì vậy số chọn thêm được tính so với các ID cũ có thể chứng minh; phần khớp sửa đỏ được thống kê riêng.

Registry: `sha256:0f2553ef01a3c6acb5b4647183c3745a75764e19fc6c6dea5bd0974d93fe4ee7`. Policy: `sha256:3cc6d1d1a3af95c0d4f3c99595f95b5f024f9f8092f65b356fc085b3588788f1`. Processing: `sha256:7aa1359fc9eea1068a6695804dea64407547995536aa7380972b0fac0eb8403d`.

Chi tiết và bằng chứng được lưu ở comparison.json, documents/*.json và registry-snapshot.json trong thư mục chạy. Ô E xanh nhạt: backend chọn thêm so với kết quả cũ; vàng nhạt: chưa resolve hoặc đã loại trừ. Mọi kết quả tự động dùng chữ đen.

Các identity cũ không còn được chọn:

| Văn bản | Identity | Raw cũ | Phân loại |
|---|---|---|---|
