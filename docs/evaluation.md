# Đánh giá nơi nhận văn bản đi

Chấm đầu ra backend **trước văn thư chỉnh sửa**. Kiểm thử deterministic xác nhận cơ chế vận hành; không chứng minh LLM đạt 95–99%.

## Gold và snapshot

Giữ hai annotation độc lập trong một record: `mentions` là tập raw token đã đối chiếu PDF; `recipient_ids` là hợp ID người/đơn vị đúng theo registry/policy snapshot hiện hành. Không học tên nhân sự hiện tại từ nhãn lịch sử. Ngày văn bản khác với thời điểm snapshot resolution.

```json
[
  {
    "document_id": "example-1",
    "annotation_complete": true,
    "gold_reviewed": true,
    "registry_version": "sha256:fixed-snapshot",
    "alias_policy_version": "sha256:fixed-policy",
    "mentions": ["Chủ tịch UBND tỉnh", "Sở Y tế"],
    "recipient_ids": ["internal_person_example", "comm_unit_example"],
    "recipient_mention_count": 2,
    "registry_eligible_mention_count": 2
  }
]
```

ID minh họa phải thay bằng ID thật trong snapshot được chấm. `extraction_annotation_complete` và `resolution_annotation_complete` có thể tách riêng; thiếu một annotation không biến annotation kia thành lỗi. `annotation_complete=false` hoặc `exclude_reason` loại record và báo số lượng/lý do. Nếu đưa `historical_labels` chứa `...` hoặc `…`, evaluator loại record trừ khi `gold_reviewed=true` chứng minh gold đã được annotate lại đầy đủ. Không dùng display string bị cắt làm danh sách ID.

Prediction là mảng `OutgoingResult` hoặc job envelope `{document_id,status,result,error}`. Có thể dùng `.jsonl`. Giữ thất bại/missing prediction trong mẫu số của ca đã annotate, không chỉ chấm job completed. Envelope phải completed và có result; queued/extracting/resolving hoặc completed thiếu result không được tính đúng, kể cả gold rỗng. Registry/policy version khác gold được tính lỗi resolution và báo riêng; extraction raw vẫn được chấm độc lập vì không phụ thuộc nhân sự trong snapshot.

```powershell
.venv\Scripts\python.exe tools/evaluate_outgoing.py --gold .tmp/gold.json --predictions .tmp/predictions.json --output .tmp/evaluation.json
```

## Metric

- Exact set match theo văn bản là tỷ lệ toàn bộ hợp ID dự đoán bằng đáp án, không thiếu/thừa. Đây là metric mục tiêu ≥95% trên holdout khóa; 99% là mục tiêu cao hơn, chưa phải kết quả.
- Precision/recall micro tính trên tập ID; dedupe ID trước tính. Mention metric độc lập dùng raw NFC, không phân biệt hoa/thường, gom khoảng trắng và bỏ dấu chấm/phẩy cuối. Giữ token annotation nhất quán khi tách tên viết tắt/danh sách; evaluator không tự thay raw bằng tên chuẩn.
- Báo số ca scored/excluded/truncated/missing/failed/version mismatch, review document rate, unresolved rate và Wilson 95% CI cho exact match. Metric không có mẫu số trả null.
- Registry coverage chỉ tính khi gold có `recipient_mention_count` và `registry_eligible_mention_count`; không suy ra từ số ID vì một group mention có thể mở thành hàng trăm ID.

Khóa train/rules, validation và holdout theo thời gian; giữ văn bản/nhóm mẫu trùng không xuyên tập. Ưu tiên văn bản mới nhất. Annotate lại 14/100 nhãn mẫu mới bị cắt và trường hợp 12418 thiếu Lâm Hải Giang trong lịch sử. Gold extraction 12355 giữ cả bốn đơn vị Kính gửi; không bỏ hai Hội chỉ vì đáp án lịch sử không ghi. 12349 PDF ghi PVPQT; 12402 giữ selector nhóm lãnh đạo/chuyên viên. VT và portfolio chưa xác nhận là thiếu policy, không tự loại để làm điểm đẹp.

Challenge set phải có scan, text có vùng nhận là ảnh, NFD/khoảng trắng trong chữ, Như trên thiếu Kính gửi, reference tới nội dung, group thiếu/đổi membership, tên cũ không có DB, đơn vị cùng tên khác sphere và provider lỗi. Tài liệu thư đối ngoại không có Nơi nhận cần đánh giá riêng; không suy ra luồng gửi nội bộ từ chữ ký.

Offline không có key: rule extraction luôn partial và giữ bằng chứng; diagnostic giúp kiểm tra coverage, không giả lập LLM complete. Khi đánh giá provider thật, ghi model/prompt/extractor và snapshot version; chỉ chạy khi môi trường cloud/key đã được cấu hình. Không gửi key qua chat hoặc ghi trong báo cáo.

Tham chiếu tới nội dung ngoài Kính gửi/Nơi nhận hiện giữ unresolved/partial: một chuỗi reference do model tự tạo chưa đủ chứng minh người trong nội dung/chữ ký là nơi nhận. OpenRouter adapter tắt context compression tự động để tránh âm thầm cắt mất vùng nhận; lỗi vượt context cần được báo và review.

## Nghiệm thu VPUB theo snapshot

- Với văn bản lịch sử, kiểm tra riêng người nhận nội bộ và danh sách chọn trên iDesk. Mục Thông tin liên thông giúp xác minh mã của các đơn vị giao liên thông. Dòng trong `book.receiver` có thể bị cắt, và có thể gồm đích nghiệp vụ không xuất hiện trong bảng giao liên thông. Đối chiếu nguồn đầy đủ trước khi đánh dấu một văn bản đã rà nhãn.
- Mỗi văn bản nghiệm thu cần `document_id`, `input_sha256`, `published_date`, `template_family`, `pdf_evidence_source`, `recipient_evidence_source`, hai cờ `annotation_complete` và `gold_reviewed` bằng true, cùng ba danh sách `mentions`, `pdf_recipient_ids` và `recipient_ids`. Bộ phát triển/validation cần bốn trường đầu để kiểm tra trùng mẫu.
- Dùng đúng snapshot có `recipient_expansions` và `unit_groups`. Prediction từ API mang phiên bản xử lý trong `result.audit.processing_version`. Khi ghi JSONL, gắn `document_id` của yêu cầu vào cả bản ghi job lỗi để giữ chúng trong mẫu số.

```powershell
.venv\Scripts\python.exe -m tools.lock_recipient_holdout --reviewed reviewed.json --development development.json --snapshot registry-snapshot.json --processing-version <version> --output holdout.json
.venv\Scripts\python.exe -m tools.evaluate_outgoing --gold holdout.json --predictions predictions.jsonl --snapshot registry-snapshot.json --output score.json
```

Bộ chấm chỉ báo đạt mốc 95% hoặc 99% khi manifest nguyên vẹn, có ít nhất 500 ca đủ nhãn và kết quả dùng đúng phiên bản đã khóa. Kết quả theo tên trên 500 ca Test 1 phục vụ hồi quy. Dùng `python -m tools.replay_vpub_coverage --help` để xem cách phát lại checkpoint cũ tại máy.
