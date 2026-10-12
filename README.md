# Outgoing recipient backend

Backend cho Script-Idesk ban hành văn bản: đọc tài liệu chính, giữ bằng chứng từng mention, tra danh bạ hiện tại và trả hợp danh sách người/đơn vị. Chưa tự chia xử lý/theo dõi và chưa huấn luyện model. Backend không click gửi chính thức trên iDesk.

## Cài đặt và chạy

Python 3.12 trở lên. PowerShell tại repo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m ai_document_sender serve
```

Mặc định chạy `127.0.0.1:8001`, offline, không gửi tài liệu ra OpenRouter. Biến môi trường của process ưu tiên hơn `.env`; đường dẫn tương đối theo repo. API dùng `X-API-Key` khi có `SENDER_API_KEY`. Bind ngoài loopback bắt buộc cấu hình key. Không đưa key OpenRouter vào Script-Idesk.

Để thử cloud, chỉnh `SENDER_PROVIDER_MODE=cloud`, `OPENROUTER_API_KEY`, `OPENROUTER_TEXT_MODEL`, và model vision nếu cần trong `.env` backend. Chọn model còn hoạt động, hỗ trợ JSON/vision và hạn mức phù hợp; không có fallback tự động sang model trả phí. Bản offline giữ phần deterministic có thể đọc, trả partial/review khi chưa chứng minh đủ; không phải chế độ đạt 95–99%.

PDF text dùng pypdf/pdfplumber. Vision scan/hybrid cần Poppler `pdftoppm` trong PATH hoặc thư mục `SENDER_POPPLER_PATH`. Không cần GPU. Thiếu renderer/model/key sẽ có lý do chưa đọc đủ, không trả danh sách rỗng như thành công đầy đủ.

### OCR cục bộ bằng VietOCR

Để đọc nhanh các trang không có lớp chữ, bật `SENDER_OCR_BACKEND=vietocr` trong `.env`.
Trang có chữ vẫn đọc trực tiếp. Trang scan dùng model PP-OCRv4 qua ONNX Runtime/OpenCV
**chỉ để phát hiện vị trí dòng**, sau đó [VietOCR](https://github.com/pbcquoc/vietocr)
`vgg_seq2seq` nhận dạng chữ tiếng Việt.
Model được giữ trong RAM và nhận dạng theo batch. `SENDER_OCR_DEVICE=auto` chọn CUDA khi
PyTorch hỗ trợ GPU, nếu không dùng CPU; có thể đặt `cpu` hoặc `cuda:0`.

PowerShell tại repo (VietOCR upstream đọc README theo UTF-8 khi cài đặt):

```powershell
$env:PYTHONUTF8 = '1'
# Máy NVIDIA có driver hỗ trợ CUDA 12.6; bỏ dòng này nếu chỉ dùng CPU.
.\.venv\Scripts\python.exe -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pip install -e ".[ocr]"
.\.venv\Scripts\python.exe -m ai_document_sender prepare-ocr
```

```dotenv
SENDER_OCR_BACKEND=vietocr
SENDER_OCR_DEVICE=auto
SENDER_OCR_BATCH_SIZE=16
SENDER_OCR_WEIGHTS=var/models/vgg_seq2seq.pth
```

Khởi động lại backend sau khi đổi cấu hình. Các trang scan đã OCR cục bộ được gửi dưới
dạng **chữ** tới `OPENROUTER_TEXT_MODEL` để phân tích nơi nhận, không gửi ảnh tới model
vision. Chế độ offline cũng nhận được phần trích xuất theo rule từ chữ OCR.
Lần đầu cần thời gian nạp model; các lượt tiếp theo dùng lại model. Không tự tải weights
khi xử lý tài liệu và không tự quay lại cloud OCR khi OCR cục bộ lỗi. Thiếu phụ thuộc,
weights, trang không đọc được hoặc độ tin cậy thấp đều giữ trạng thái cần rà soát.
Giới hạn `SENDER_MAX_VISION_PAGES` chỉ áp dụng cloud vision, không cắt số trang OCR cục bộ.
Checkpoint giữ vị trí/độ tin cậy dòng; audit lưu trang OCR, GPU/CPU và thời gian. Đổi cấu hình OCR tạo
lượt xử lý mới để tránh dùng lại kết quả cũ. Bản upstream được ghim commit vì VietOCR
0.3.13 trên PyPI khóa Pillow cũ không tương thích Python 3.14.

`Như Điều N` trong Nơi nhận được truy về đúng điều, kể cả nội dung qua nhiều trang. Backend lấy người/đơn vị chịu trách nhiệm, được giao nhiệm vụ hoặc phối hợp; danh sách các Sở được tách riêng. Tham chiếu tới các cá nhân ở điều khác có thể truy tiếp đến danh sách kèm theo, giữ bằng chứng cả chuỗi. Vision cần chép cả nội dung điều và danh sách để kiểm chứng. Thiếu điều/danh sách, tham chiếu vòng hoặc không rõ đối tượng vẫn giữ `reference` cần rà soát; số điều không được dùng làm tên người/đơn vị. Người ký, cơ quan công tác trong danh sách cá nhân và đối tượng chỉ được nhắc trong diễn giải nhiệm vụ không tự trở thành nơi nhận.

## API outgoing.v1

`GET /health`: schema, hai version registry/policy, provider capability và giới hạn. `POST /v1/outgoing/jobs`: multipart PDF `file` và `metadata` JSON, bắt buộc header `Idempotency-Key`. Metadata cần `document_id`; có thể thêm `sign_number`, `subject`, `document_date`, `issuer`, `department_code`, attachment UID/name. Client tải PDF trong phiên iDesk trước rồi upload bytes; backend không nhận URL/cookie/mật khẩu iDesk.

Tạo job trả 202 `{job_id,status}`. Cùng key/cùng tài liệu/context/snapshot và phiên bản xử lý trả job cũ; khác tài liệu/context/snapshot trả 409. Backend tạo lượt mới khi extractor, prompt, model, chế độ provider hoặc giới hạn đọc thay đổi, kể cả với userscript cũ. Job đang chạy được dùng lại để tránh xử lý trùng; job/kết quả/feedback cũ vẫn giữ để đối chiếu. Sau khi job failed, muốn thử lại cùng phiên bản xử lý phải dùng key mới. Tạo key từ document ID, file hash và cả hai version ở health. Version danh bạ đổi vẫn có thể dùng lại extraction cache.

`GET /v1/outgoing/jobs/{job_id}` trả `{job_id,status,result,error}`. Status: queued/extracting/resolving/completed/failed. Result có `people`, `units`, `mentions`, `unresolved`, `excluded`, bằng chứng, version và `resolution_as_of`. Completed nghĩa xử lý xong; `needs_review` vẫn true nếu partial/failed/unresolved hoặc có cảnh báo. Giao diện phải kiểm tra hai version và identity thực trên iDesk trước khi điền.

`GET /v1/outgoing/recipients/search?q=...&limit=10` trả `{items,registry_version,alias_policy_version}` phục vụ thêm người/đơn vị thủ công. Kết quả tra là ứng viên, không tự chọn top-1.

`POST /v1/outgoing/jobs/{job_id}/feedback` nhận `registry_version`, `alias_policy_version`, `final_recipients`, `field_assignments`, `review_decisions`, `edits`, `confirmed`; trả 201 `{feedback_id}`. Identity phải đúng snapshot. Decision `resolve` cần `recipient_ids` không rỗng, trỏ tới các ID trong danh sách cuối; không thể đánh dấu đã resolve mà không có người/đơn vị nào. Các lý do toàn cục dùng `mention_id="reason:<review_reason>"`, action `accept_missing`, note rõ; mọi unresolved phải được quyết định trước confirmed. Feedback append-only, không tự sửa rule hoặc gửi văn bản. Schema chi tiết ở `/docs` và [đặc tả](docs/superpowers/specs/2026-10-07-outgoing-backend-design.md).

## Directory và policy

DB nguồn `resources/data/lookup.db` chỉ được mở đọc. Người theo role/mã được tìm từ snapshot hiện hành, độc lập ngày tài liệu cũ. V1/V5/V8 được tách đúng token trong chức danh và phòng tương ứng; không khóa tên cán bộ trong lịch sử. PCT/PCVP nhiều người, portfolio PVPQT/PVPVX/PCVP XD chưa verified và VT chưa rõ nghĩa luôn cần rà soát. Không tìm được trong DB không chứng minh đã giải thể/nghỉ việc.

Nếu `department_code` trống, backend chỉ lấy mã phòng đã xác minh từ số/ký hiệu đúng dạng số nguyên `/UBND-<mã phòng>`, ví dụ `12355/UBND-KGVX`. Metadata phòng được cung cấp luôn ưu tiên; hậu tố chưa biết hoặc UUID không tạo context. Nguồn context nằm trong `audit.resolution_context`; backend không tự suy ra cơ quan phát hành từ ký hiệu này.

Một đơn vị có thể có nhiều code/sphere. `source_id` của comm record là UUID nguồn lịch sử, không phải ID node giao diện. Client chọn bằng code+sphere rồi kiểm tra chip. Thiếu group membership phải unresolved; không đổi selector nhóm thành group node để che thiếu người.

Quản trị viên có thể import overlay **đã xác nhận từ iDesk** qua CLI local; không có API ghi alias:

```powershell
.\.venv\Scripts\python.exe -m ai_document_sender import-overlay verified-overlay.json
```

File là JSON list. Mỗi mục có `verification_status="verified"`, `verified_by`, `evidence` và một trong:

- `recipient`: identity theo schema Recipient, gồm code/sphere/source_id; dùng ID mới có namespace riêng khi thêm đơn vị ngoài DB.
- `selector` và `member_ids`: membership đã xác nhận, trỏ tới ID tồn tại.
- `selectable_group_id`: xác nhận một INTERNAL_GROUP thật sự chọn được như một đơn vị, không thay thế việc expand selector tập người.

Policy alias versioned ở `resources/policies/recipient_aliases.v1.json`. Chỉ alias verified đúng scope và còn hiệu lực được áp dụng. Sửa overlay/DB/policy sẽ làm version đổi khi health/job mới đọc, không cần restart. Job cũ giữ snapshot riêng; feedback stale bị 409.

## Vận hành và kiểm chứng

Một worker dùng SQLite transaction/lease, heartbeat và checkpoint. Restart phục hồi lease hết hạn; poll không tạo job mới. Cache extraction chỉ chia sẻ khi complete, theo file/context/extractor/prompt/model; result được giữ theo idempotency fingerprint có registry+policy và phiên bản xử lý. Runtime nằm trong `var/` đã ignore; bảng job cũ được bổ sung thông tin phiên bản khi khởi động. Bấm Phân tích sau khi nâng phiên bản sẽ tạo job mới thay vì trả kết quả cũ. Khi khởi động, dữ liệu PDF/checkpoint/cache quá `SENDER_RETENTION_DAYS` được dọn nếu không thuộc job còn chạy; result/snapshot/feedback vẫn giữ làm audit. Không dùng đồng thời nhiều process Uvicorn với MVP.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests dùng DB mini/PDF sinh và provider giả, không gọi cloud. Đọc [quy trình đánh giá](docs/evaluation.md) để annotate mention và identity riêng, ưu tiên tài liệu mới. Chưa có holdout hoàn chỉnh và chạy model thật thì không được tuyên bố đã đạt mục tiêu 95–99%.
