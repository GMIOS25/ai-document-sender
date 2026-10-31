# Học nơi nhận VPUB từ đối soát văn thư ngày 31/10/2026

Đã tích hợp dữ liệu từ [Google Sheets, tab Thống kê, A1:F5140](https://docs.google.com/spreadsheets/d/1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s/edit?gid=0#gid=0) vào backend và SQLite VPUB tại workspace này. Sheet nguồn có 500 văn bản, 5.138 dòng dữ liệu và 1.579 dòng sửa đỏ. File Google Sheets không bị sửa.

Bộ quy tắc nằm tại `resources/tenants/vpub/recipient_learning.v1.json`. Có 350 quy tắc được tổng hợp; 186 quy tắc hiện đủ điều kiện áp dụng, bao phủ 933 dòng sửa đỏ. Mỗi quy tắc lưu dòng nguồn, phạm vi cơ quan, qualifier và section đã quan sát. Đây là học bằng quy tắc đã đối soát; không huấn luyện lại trọng số mô hình OpenRouter.

| Trạng thái của dòng sửa đỏ | Số dòng |
|---|---:|
| Đủ identity duy nhất, áp dụng được | 933 |
| Có ít nhất một đích thiếu trong danh bạ | 320 |
| Có ít nhất một đích trùng nhiều identity | 225 |
| Mâu thuẫn hoặc selector quá chung | 77 |
| Mã cán bộ phải tra danh bạ hiện hành, tham chiếu hoặc lỗi trích xuất | 24 |
| Tổng | 1.579 |

Ví dụ đã áp dụng: PVPQT → Trương Công Hoài, PVPXD → Phan Đình Hải, PVPNN → Trần Đình Triết, PVPVX → Võ Gia Nghĩa, PVPTH → Lê Huy Vũ; “các PCT UBND tỉnh” → sáu người đã được đối soát; TC có qualifier Sở → Sở Tài chính Gia Lai. Các nhóm CVP/PCVP có lĩnh vực cụ thể được giữ đúng danh sách của selector, không mở rộng thành toàn bộ Văn phòng.

Resolver ưu tiên quy tắc đã đối soát khi cơ quan phát hành và section/qualifier phù hợp. Nếu một đích biến mất, đổi tên/chức vụ/mã hoặc có nhiều identity phù hợp, cả ánh xạ đó được giữ unresolved. Nhóm chỉ được trả khi tất cả thành viên khớp duy nhất. Không tự tạo `source_id`, UUID hay code từ tên cơ quan. Các đích còn thiếu được lưu bằng tiêu chí tên/mã để có thể đối chiếu lại khi danh bạ được bổ sung. Danh sách người đã học phản ánh lần đối soát này; khi phân công hoặc thành viên nhóm thay đổi cần rà soát lại quy tắc nhóm.

Đã bổ sung 10 viết tắt vào `ABBREVIATIONS`, mở rộng từ khóa hai chiều theo ranh giới từ, lập chỉ mục trong bộ nhớ cho tên/mã/chức vụ/tên đơn vị địa phương, và cập nhật `search_text` cùng `recipients_fts` cho 1.693 identity hiện có. Đã xác minh mọi trường identity ngoài `search_text` giữ nguyên và SQLite kiểm tra toàn vẹn thành công. Đồng bộ sau này tính cả phiên bản từ điển/quy tắc; khi chúng thay đổi vẫn xây lại chỉ mục dù dữ liệu danh bạ không đổi. Mã chuyên viên, email và rank từ nguồn được giữ trong chỉ mục.

Phát lại toàn bộ dòng sheet, sử dụng raw, qualifier và section ghi trong ô, không gọi cloud: trong 1.028 dòng đỏ có thể xác định duy nhất toàn bộ đích, số dòng khớp đầy đủ tăng từ 0 lên 933. 95 dòng còn lại tiếp tục cần rà soát. Không có dòng đỏ nào trả danh sách không rỗng khác với đích đã xác định trong phép phát lại. Cả 2.710 dòng đen có `recipient_id` trong ghi chú đều giữ được identity đó; 23 dòng đen còn lại không có ghi chú ID để kiểm tra theo tiêu chí này. Tổng thời gian resolver của phép phát lại giảm từ 9,96 xuống 6,03 giây khi bật học. Đây là đối chiếu lại dữ liệu đã học, không phải độ chính xác trên tài liệu mới hoặc thời gian OCR/LLM toàn quy trình. Chưa chạy lại 500 PDF qua OpenRouter; ghi chú sheet còn nêu nhiều lần lỗi provider trước đó.

Toàn bộ suite: **177 tests passed**. Review độc lập không còn phát hiện P1/P2. Dữ liệu tổng hợp và các dòng cần xem lại nằm tại `reports/recipient-learning-vpub-2026-10-31.json`; danh sách 140 tiêu chí đích chưa khớp duy nhất (126 thiếu, 14 trùng) nằm tại `reports/recipient-learning-vpub-pending-2026-10-31.csv`. Một đích có thể xuất hiện trong nhiều dòng và nhóm khác nhau.

Một số dòng cần quyết định nghiệp vụ: E4 có thêm Thanh tra tỉnh ngoài danh sách xã/phường; E155 ghi Bộ Y tế dù D155 có qualifier Sở; “Chủ tịch” có kết quả cá nhân và kết quả cả nhóm; “PCT UBND tỉnh” số ít được sửa thành sáu người. Những ánh xạ này được giữ để rà soát, không chọn theo đa số. Các tên Công an tỉnh, Ban Tiếp Công dân và Trung tâm Phục vụ hành chính công còn trùng các identity/sphere khác nhau; cần xác nhận đích tuyến gửi cụ thể. Thanh tra tỉnh, Sở Ngoại vụ và nhiều UBND xã/phường đang thiếu identity thực sự trong DB.

Để tái tạo từ snapshot CellData đã đọc bằng connector:

```powershell
.\.venv\Scripts\python.exe tools/learn_recipient_sheet.py --source .tmp/vpub_sheet_learning_source_2026-10-31.json --output var/recipient-learning/preview
.\.venv\Scripts\python.exe -m tools.evaluate_recipient_learning --source .tmp/vpub_sheet_learning_source_2026-10-31.json --policy var/recipient-learning/preview/recipient_learning.v1.json --output var/recipient-learning/preview/replay.json
```

Thêm `--apply` vào lệnh đầu để cài bộ quy tắc sau khi xem preview. CLI không gọi Google/LLM; snapshot đầu vào phải được đọc lại từ sheet khi cần học sửa đổi mới. Snapshot gốc ở `.tmp` không được đưa vào Git; file quy tắc đã cài lưu SHA-256 để đối chiếu nguồn. Lần áp dụng này đã lưu bản SQLite trước thay đổi tại `var/recipient-learning/vpub-2026-10-31/lookup.before-learning.db`. Với lần cài đầu này, có thể gỡ file quy tắc rồi khôi phục DB từ bản sao trên khi backend đã dừng; với lần cập nhật tiếp theo phải khôi phục cả policy trước đó. Không dùng bản sao cũ nếu sau đó danh bạ đã có thay đổi mới cần giữ lại.

Backend đang chạy phải được khởi động lại để nhận mã Python mới. Sau đó sửa file quy tắc sẽ làm cache policy hết hiệu lực khi đọc registry lần kế tiếp. Job cũ vẫn giữ snapshot cũ; cần tạo lượt phân tích mới để nhận quy tắc mới.


Cập nhật sau xác nhận tuyến Công an tỉnh ngày 31/10/2026: người dùng chọn **Trong tỉnh — G01.035.000.000**. Policy lưu xác nhận tại `target_routes`; tên chưa có code/sphere được ràng buộc lại với identity có đúng tên, code, sphere và loại. Tiêu chí đích đã ghi code/sphere cụ thể vẫn được giữ nguyên. Compiler giữ lại xác nhận này khi học lại sheet. Hiện có 187 quy tắc áp dụng được, bao phủ 1.005 dòng đỏ; số liệu 186/933 ở phần trên là kết quả của lần tích hợp đầu.

Đã sửa trường hợp Nơi nhận dẫn tới Điều/Mục trong nội dung: quy tắc dành cho `noi_nhan` cũng nhận bằng chứng `body_reference` khi mention giữ được bằng chứng Nơi nhận gốc khớp chuỗi `references`. Một mention chỉ có nội dung thân văn bản hoặc dẫn chiếu không khớp vẫn bị chặn. Resolver version v5 làm lượt phân tích mới dùng cách xử lý mới.

Đã phát lại toàn bộ mentions của job `3550/QĐ-UBND` bằng registry hiện tại: Công an tỉnh được chọn tự động với mã `G01.035.000.000`, đúng sphere `int_province_comm`; toàn bộ identity đã chọn trước đó vẫn được giữ. Không sửa kết quả/snapshot của job cũ. Bản sao policy/SQLite trước xác nhận tuyến và kết quả phát lại nằm tại `var/recipient-learning/vpub-2026-10-31/` với tên `policy.before-cong-an-route.json`, `lookup.before-cong-an-route.db`, `3550-resolution-after-cong-an-route.json`. Suite sau sửa: **181 tests passed**.
