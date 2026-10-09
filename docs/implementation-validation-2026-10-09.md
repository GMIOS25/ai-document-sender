# Kiểm chứng triển khai backend — 09/10/2026

## Phạm vi và kiểm thử

Backend MVP trả **hợp danh sách người và đơn vị**, giữ mention/bằng chứng và đối chiếu danh bạ hiện hành. Chưa phân vai xử lý/theo dõi, chưa huấn luyện model. Kiểm chứng dưới đây chạy offline; **0 cuộc gọi provider**, không gọi hệ thống iDesk để gửi văn bản.

Lệnh tại repo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kết quả ngày 09/10/2026: **59 passed, 1 warning**. Warning là deprecation của Starlette TestClient/httpx; không có test thất bại. Tests dùng DB fixture, PDF sinh và provider giả; không chứng minh chất lượng LLM trên tài liệu thật.

Kiểm tra liên repo bằng Node provider thật gọi FastAPI trên loopback cũng đạt: multipart PDF 12355 → tạo/poll job → lặp lại dùng cùng job → tìm danh bạ → feedback có `recipient_ids` liên kết ứng viên. Metadata client chỉ có số hiệu `/UBND-KGVX` vẫn resolve V1/V5/V8 qua fallback mã phòng đã xác nhận. Kết quả: 13 mentions, 6 người, 1 đơn vị, 6 unresolved, `partial`; 0 cloud calls và 0 lần gửi iDesk. Danh sách/feedback của lượt này chỉ dùng kiểm giao thức, không phải phê duyệt nghiệp vụ.

Các kiểm thử có ý nghĩa bao gồm: snapshot hiện hành và DB chỉ đọc; chức danh duy nhất/đồng danh/mã chuyên viên; alias chưa xác nhận hoặc xung đột; selector nhóm thiếu membership; Như trên/Lưu và chữ ký; scan/hybrid/Unicode; grounding và schema; retry/timeout/allowlist; idempotency/lease/checkpoint/cache; feedback sai identity/version hoặc resolve không liên kết ID; evaluator giữ ca thất bại/chưa hoàn thành trong mẫu số. Hai lỗi phát hiện qua review độc lập đã có regression: reference tự tạo không thể biến người ký thành nơi nhận, và job queued/completed thiếu result không thể chấm đúng gold rỗng.

## Chẩn đoán trên năm PDF thật

Nguồn: [thư mục mẫu](../resources/văn%20bản%20mẫu/vpub/Hợp%20lệ/). Bộ đọc deterministic lấy mention từ text/layout; không có OCR/model thật trong lượt này. Mọi ca đều `partial`, `needs_review=true`.

| Văn bản | Trang | Mentions | Người | Đơn vị | Unresolved |
|---|---:|---:|---:|---:|---:|
| 12355UBND-KGVX | 1 | 13 | 6 | 1 | 6 |
| 12349UBND-KGVX | 2 | 13 | 6 | 4 | 3 |
| 12418UBND-KGVX | 1 | 9 | 5 | 2 | 2 |
| 12402UBND-KTTH | 1 | 10 | 2 | 1 | 7 |
| 12408UBND-NNMT | 2 | 0 | 0 | 0 | 0 |

Unresolved không có nghĩa là người đã nghỉ hoặc đơn vị đã giải thể; đó là kết quả chưa được xác định đủ từ snapshot/policy hiện tại.

- **12355**: Hội Văn học Nghệ thuật tỉnh, Hội Nhà báo tỉnh, Báo và Phát thanh - Truyền hình Gia Lai, Phòng QTTV-VP UBND tỉnh: `not_in_registry`; PVPQT: `unverified_business_alias`; VT: `policy_unknown`.
- **12349**: Bộ Chỉ huy Quân sự tỉnh: `ambiguous_registry_identity` vì có nhiều identity phù hợp; PVPQT: `unverified_business_alias`; VT: `policy_unknown`.
- **12418**: PVPVX UBND tỉnh: `unverified_business_alias`; VT: `policy_unknown`. Hai PCT được ghi trong PDF đều giữ lại; không lấy nhãn lịch sử thiếu một người làm đáp án hiện hành.
- **12402**: Thường trực HĐND tỉnh và C5: `not_in_registry`; các PCT UBND tỉnh, Các Sở/ban/ngành thuộc tỉnh, Lãnh đạo VP+CV VP UBND tỉnh, UBND các xã/phường: `missing_group_membership`; VT: `policy_unknown`.
- **12408**: PDF scan, không có mention đọc được khi offline. `unresolved=0` không phải đầy đủ; các lý do `recipient_sections_missing`, `provider_unavailable`, `unreadable_region`, `extraction_partial` bắt buộc review.

Bốn PDF có text đều có `provider_unavailable`, `extraction_partial`. Tham chiếu tới nội dung ngoài vùng nhận hiện được giữ để review (`unsupported_reference`) cho tới khi có liên kết nguồn–đích được kiểm chứng.

Artifact chi tiết local, đã ignore: [outgoing-task2-diagnostics.json](../.tmp/outgoing-task2-diagnostics.json); script tái chạy: [outgoing_task2_diagnostics.py](../.tmp/outgoing_task2_diagnostics.py). Đây là diagnostic, không phải gold và không thay cho holdout.

**DB nguồn không đổi**: SHA-256 trước/sau lượt diagnostic và sau kiểm thử đều là:

```text
a0fa4cac0b48e2ec07a5f438b1d1921fee879598a8334328af21006ef29b879f
```

Hash được kiểm lại bằng `Get-FileHash resources/data/lookup.db -Algorithm SHA256`. Diagnostic ghi `db_unchanged=true`, `provider_calls=0`.

## Chạy qualification có model và evaluator

Đọc [quy trình đánh giá](evaluation.md) trước khi chấm. Chuẩn bị gold đã rà PDF đầy đủ, có hai annotation độc lập `mentions`/`recipient_ids`, cùng `registry_version`/`alias_policy_version` của snapshot khóa. Đáp án TXT lịch sử chỉ là tham khảo: nhãn cắt `...`, tên cũ, khác biệt nghiệp vụ mặc định và thiếu người phải được annotate lại. Không xóa ca scan, nhóm khó, thiếu DB hay provider lỗi để tăng điểm.

Để chạy cloud, cấu hình `.env` backend từ [.env.example](../.env.example), đặt `SENDER_PROVIDER_MODE=cloud`, key và hai model đang hoạt động hỗ trợ structured JSON/text hoặc vision. Cấu hình Poppler khi đọc scan/hybrid. Không ghi key vào report hoặc frontend. Adapter chỉ dùng model đã cấu hình, không fallback sang model trả phí; có timeout/retry/repair giới hạn, validation local và grounding. Lượt kiểm chứng trong report này **chưa chạy bước cloud**.

```powershell
.\.venv\Scripts\python.exe -m ai_document_sender serve
```

Dùng client upload bytes PDF chính qua `POST /v1/outgoing/jobs` với metadata đã rà, `Idempotency-Key` mới và `X-API-Key` nếu đã cấu hình; poll `GET /v1/outgoing/jobs/{job_id}` đến completed/failed. API/schema chi tiết ở [README](../README.md) và `/docs`. Lưu prediction trước chỉnh sửa thủ công, không loại job failed. Envelope failed cần thêm `document_id` từ manifest để evaluator giữ đúng ca trong mẫu số.

Model/prompt/extractor, snapshot và PDF hash phải được ghi cùng mỗi lượt qualification. Đánh giá ít nhất cả text, scan, hybrid, Như trên, nhóm, alias chưa xác nhận và đơn vị trùng tên/sphere; giữ holdout theo thời gian và không để cùng mẫu/nhóm tài liệu xuyên tập. Registry đổi thì khóa lại gold resolution và chạy lại; extraction raw có thể chấm riêng.

```powershell
.\.venv\Scripts\python.exe tools/evaluate_outgoing.py --gold .tmp/gold-reviewed.json --predictions .tmp/predictions-cloud.json --output .tmp/evaluation-cloud.json
```

Evaluator chấm exact set match theo văn bản, precision/recall của mentions và ID, tỷ lệ review/unresolved, phiên bản sai, thất bại và Wilson 95% CI. Mục tiêu ≥95% exact set match trên holdout khóa là **điều kiện cần đo**, 99% là mục tiêu cao hơn. 59 tests và năm lượt offline không đủ cơ sở tuyên bố đã đạt 95–99%.

Protocol adapter đã đối chiếu nguồn chính thức: [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [image input](https://openrouter.ai/blog/tutorials/send-image-to-llm/), [Retry-After/error handling](https://openrouter.ai/docs/api_reference/errors-and-debugging). [Context compression](https://openrouter.ai/docs/guides/features/message-transforms) được tắt để tránh âm thầm cắt mất thông tin nhận; vượt context sẽ trả lỗi để review.
