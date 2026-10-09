# Thiết kế backend nhận diện nơi nhận văn bản đi

Ngày: 2026-10-07. Người dùng đã duyệt triển khai ngày 2026-10-09; MVP đã hiện thực và kiểm chứng offline.

## Mục tiêu và phạm vi

Nhận tài liệu chính do Script-Idesk chọn, trích xuất người/đơn vị từ Nơi nhận, Kính gửi và tham chiếu liên quan, resolve theo registry hiện hành, trả danh sách định danh đủ bằng chứng cho client. MVP chỉ cần hợp người và đơn vị; chưa tự phân xử lý/theo dõi và chưa huấn luyện mô hình.

Mục tiêu 95–99% cần được kiểm chứng trên bộ holdout đã làm sạch. Không coi số này là kết quả đạt được trước khi chạy đánh giá. Ưu tiên tài liệu mới nhất, dùng lịch sử làm ví dụ cách viết, không coi nhân sự cũ là mapping hiện tại.

Client được tổ chức theo [đặc tả hai workflow](../../../../Script-Idesk/docs/superpowers/specs/2026-10-07-dual-workflow-design.md). HTTP contract outgoing độc lập với router tiếp nhận hiện có.

## Kiến trúc

Hybrid: extraction giữ nguyên mention và bằng chứng → chuẩn hóa alias/rule có phạm vi → truy xuất ứng viên registry → quyết định có ràng buộc → trả resolved và unresolved. Registry tham gia ở lúc tạo ứng viên, không đợi đến cuối sau khi LLM tự viết một danh sách tên chuẩn.

Python 3.12+, FastAPI, Uvicorn, Pydantic, python-multipart, HTTPX, pypdf/pdfplumber; Poppler dùng render trang khi cần vision. SQLite FTS5 cho retrieval; một worker bền vững cho MVP. Không cần GPU, vector database hoặc Redis. Giữ nguyên tools/crawler/build_lookup_db, không import module có side effect OCR toàn corpus.

```text
src/ai_document_sender/
  config.py                  # env, paths, limits
  contracts.py               # API + mention + result validation
  api.py                     # multipart/jobs/feedback/health
  jobs.py                    # durable jobs, lease, retry, cache
  extraction.py              # PDF layout + regional quality + vision
  mentions.py                # sections/references/evidence
  resolver.py                # rules, candidates, constrained decisions
  registry.py                # readonly base DB + verified overlay
  provider.py                # OpenRouter adapter
resources/policies/recipient_aliases.v1.json
var/runtime.sqlite           # jobs/checkpoints/feedback/overlay
pyproject.toml
tests/
```

## Registry và policy

Mở `resources/data/lookup.db` bằng SQLite `mode=ro`. Không rebuild hoặc cập nhật DB nguồn lúc khởi động. Ghi job/feedback/directory overlay ở `var/runtime.sqlite`; ignore runtime artifacts. Snapshot DB, overlay và policy có fingerprint riêng; kết quả ghi version để tái lập.

DB hiện có người/phòng/nhóm/đơn vị và FTS, nhưng chưa có active/validity/alias/membership chuẩn. Không suy ra người đã nghỉ hay đơn vị đã giải thể chỉ vì không tìm được. `priority_score` dùng xếp ứng viên khi truy xuất, không chứng minh đúng identity.

Overlay chỉ nhận dữ liệu directory được xác nhận từ lựa chọn thực tế iDesk, kèm sphere/code/node ID/source/time. Không lấy UUID history của comm record làm node ID UI. Identity người nội bộ theo node ID/username; đơn vị theo code + sphere + recipient type. Duplicate không rõ identity phải unresolved.

Policy alias gồm raw_alias, canonical_role hoặc staff_code/recipient_id, organization_scope, department_context, valid_from, valid_to, verification_status, evidence và người xác nhận. Chỉ policy verified còn hiệu lực được auto-resolve. Feedback không tự kích hoạt policy.

Các mặc định nghiệp vụ:

| Mention | Hành vi |
|---|---|
| Chủ tịch UBND tỉnh | Expand đúng role, exact unique role trong tổ chức; nếu nhiều kết quả thì ambiguous |
| CVP | Chánh Văn phòng UBND tỉnh, khớp role chính xác; không khớp PCVP bằng substring |
| PCT UBND tỉnh không tên/không lượng từ | ambiguous_role; không tự chọn top-1 hoặc toàn bộ PCT |
| Các PCT / toàn bộ PCT | Selector nhóm; chỉ mở rộng membership hiện hành đã xác nhận |
| Tên tắt như N.T.T.Lịch | Matching tên/initials có ngữ cảnh role/org; một ứng viên đủ bằng chứng mới resolve |
| PVPQT, PVPVX, PCVP XD | unverified_business_alias đến khi văn thư xác nhận portfolio |
| V1/V5/V8 trong Lưu | Resolve cán bộ hiện tại theo mã được user xác nhận; không cố định tên cũ từ gold |
| VT trong Lưu | unresolved: policy_unknown, giữ raw evidence đến khi văn thư xác nhận ý nghĩa; chỉ excluded nếu policy lưu trữ được verified |
| VT ở dòng nhận độc lập | unresolved: ambiguous_abbreviation |
| Người được ghi tên rõ nhưng không tồn tại | not_in_registry; không thay bằng người kế nhiệm |
| Đơn vị không tồn tại | not_in_registry; không kết luận giải thể |

DB hiện tại có mã V1/V5/V8 trong nhãn/chức danh của người nội bộ. Tách token staff code có ranh giới rõ trong INTERNAL_PERSON và tổ chức/phòng tương ứng, chỉ resolve khi duy nhất; đọc người từ snapshot ở mỗi version, không cố định tên trong policy. Nếu dữ liệu sau này mất mã hoặc nhiều người cùng mã thì unresolved, cần mapping hiện tại verified riêng. Không suy ra mapping chỉ từ kết_quả_gửi_đi.txt. `resolution_as_of` là thời điểm snapshot hiện hành được dùng cho job, độc lập document_date; ngày văn bản chỉ là metadata/evidence, không dùng để tự phục dựng nhân sự lịch sử. Kết quả ghi snapshot basis; không tuyên bố validity lịch sử mà dữ liệu không cung cấp.

## Extraction và bằng chứng

1. Đọc PDF với layout và page index; xác định Kính gửi/Nơi nhận, dòng Lưu và các reference.
2. Đánh giá text theo từng vùng cần đọc. PDF có text toàn trang nhưng mất vùng Nơi nhận vẫn cần render/OCR vùng đó. PDF scan dùng vision/OCR; hybrid chỉ xử lý vùng thiếu.
3. LLM trả JSON mention, không tự gán tên người cho một chức danh và không tạo ID registry. Mention gồm raw text, kind, section, page, span/bbox nếu có, lượng từ/phạm vi, reference và qualifier.
4. `Như trên` trong Nơi nhận mở rộng Kính gửi. Tham chiếu mục/điều trong nội dung phải được lần tới nguồn cụ thể. Không resolve được reference thì ghi unsupported_reference.
5. Dòng Lưu được giữ để xử lý staff code. Không thêm người ký vào nơi nhận chỉ vì chữ ký xuất hiện. Cụm như “lãnh đạo VP + chuyên viên VP” giữ selector nhóm, không để LLM tự liệt kê từ trí nhớ.

Trạng thái extraction: complete, partial, failed. Complete nghĩa đã đọc đủ vùng bắt buộc và giải thích các tham chiếu, không nghĩa đã resolve đủ registry. Tài liệu không có Nơi nhận/Kính gửi hoặc chỉ có thư đối ngoại phải cần rà soát, không tự học routing nội bộ từ lịch sử gửi.

## Resolver

Giữ raw mention bất biến. Chuẩn hóa Unicode, dấu/khoảng trắng và alias có scope. Ưu tiên code/username/ID chính xác, tên chính xác trong tổ chức, role duy nhất, staff code verified, group membership verified. Với tên tắt/biến thể, lấy top-K candidates kèm role/org/sphere; LLM chỉ được chọn ID thuộc candidates hoặc abstain. Output ngoài candidate set bị loại và ghi review reason.

Mỗi resolved item phải truy ngược được raw phrase → reference/rule → candidate → registry identity. Dedupe theo identity có snapshot, gộp mọi evidence. Không dedupe theo display name. Không áp một canonical label vào cả trong/ngoài tỉnh khi có nhiều code.

Một miss không khiến cả job thất bại. Trả phần resolved và danh sách unresolved với reason: ambiguous_role, ambiguous_registry_identity, unverified_business_alias, policy_unknown, not_in_registry, unreadable_region, unsupported_reference, provider_unavailable hoặc invalid_model_output. Không bỏ mention âm thầm. Mỗi mention có mention_id ổn định trong một extraction để feedback trỏ đúng bằng chứng. `needs_review` luôn true khi extraction_status khác complete, unresolved không rỗng hoặc có review reason; không trả partial với needs_review=false.

## OpenRouter và chế độ offline

Provider được cấu hình qua env: OPENROUTER_API_KEY, OPENROUTER_TEXT_MODEL, OPENROUTER_VISION_MODEL, URL, timeout/retry và giới hạn tài liệu. Key ở backend. Free model là lựa chọn cho phát triển, cần kiểm tra capability text/vision/JSON và hạn mức thực tế khi cấu hình. Không khóa hệ thống vào một tên model free có thể đổi; không fallback tự động sang model trả phí.

Không có key thì health báo extraction/provider capability bị thiếu. Pipeline vẫn chạy deterministic fixtures và text/rule extraction có gắn trạng thái partial khi chưa chứng minh đủ mention; không giả lập một kết quả LLM hoàn chỉnh. Test provider dùng response giả. Upload dữ liệu thật ra provider chỉ xảy ra khi người dùng cấu hình chế độ provider cloud và chạy job.

Retry có giới hạn cho 429/5xx/network, tôn trọng Retry-After trong ngân sách timeout. Invalid JSON được validate và một lần repair có giới hạn; không che lỗi bằng mảng rỗng. Vision không hỗ trợ thì partial/unreadable rõ ràng. Model/version/prompt version và request timing được ghi trong audit, không log key/cookie.

## HTTP contract outgoing.v1

Backend mặc định bind 127.0.0.1:8001. Client tải tài liệu từ iDesk và gửi bytes; server không nhận URL/cookie/credentials để tải thay. Cấu hình API key dùng X-API-Key khi có; triển khai ngoài loopback bắt buộc có key. Giới hạn mặc định 20 MiB/PDF, 100 trang, cấu hình được; file không hợp lệ trả 4xx có mã lỗi.

### Tạo job

`POST /v1/outgoing/jobs`: multipart `file`, `metadata` JSON; header Idempotency-Key bắt buộc.

```json
{
  "document_id": "idesk-document-id",
  "sign_number": "12355/UBND-KGVX",
  "subject": "Lựa chọn hình ảnh in lịch Tết",
  "document_date": "2026-10-05",
  "issuer": "UBND tỉnh Gia Lai",
  "department_code": "KGVX",
  "attachment_content_uid": "content-uid",
  "attachment_name": "main.pdf"
}
```

Document ID và file bắt buộc; các trường khác optional, không tự bịa ngày phát hành từ PDF trắng header. HTTP 202 trả `{job_id,status:"queued"}`. Cùng key/cùng fingerprint trả job cũ; cùng key/khác fingerprint trả 409. Fingerprint gồm workflow, file hash, metadata dùng trong resolution và registry_version/alias_policy_version chụp lúc tạo job. Client lấy hai version từ health để cấu thành key; khi version thay đổi, tạo key mới và vẫn dùng lại extraction cache. Phiên bản thực sự job dùng được trả trong result; client kiểm tra lại trước fill để xử lý race cập nhật directory.

### Đọc job

`GET /v1/outgoing/jobs/{job_id}` trả envelope `{job_id, status, result, error}`. Status là queued, extracting, resolving, completed hoặc failed. result/error mặc định null; completed có result theo JSON dưới đây, failed có error `{code,message,retryable}`. Không tìm được job trả 404. Completed chỉ là pipeline kết thúc; client phải đọc needs_review.

```json
{
  "schema_version": "outgoing.v1",
  "job_id": "job-id",
  "document_id": "idesk-document-id",
  "input_sha256": "file-hash",
  "registry_version": "sha256:registry-with-overlay",
  "alias_policy_version": "sha256:policy",
  "resolution_as_of": "2026-10-07T00:00:00Z",
  "extraction_status": "complete",
  "mentions": [
    {"mention_id": "mention-id", "raw": "Chủ tịch UBND tỉnh", "kind": "role", "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Chủ tịch UBND tỉnh"}], "references": []}
  ],
  "people": [
    {
      "recipient_id": "internal_270",
      "source_id": "270",
      "recipient_type": "INTERNAL_PERSON",
      "name": "Phạm Anh Tuấn",
      "role": "Chủ tịch UBND tỉnh",
      "sphere": "internal",
      "code": "tuanpa@vpub.gialai.gov.vn",
      "match_method": "exact_unique_role",
      "evidence": [{"page": 1, "section": "noi_nhan", "raw": "Chủ tịch UBND tỉnh"}]
    }
  ],
  "units": [],
  "unresolved": [],
  "excluded": [],
  "needs_review": false,
  "review_reasons": [],
  "timings_ms": {}
}
```

`units` dùng cùng identity/evidence contract và có thể là INTERNAL_DEPT/INTERNAL_GROUP/INTERNAL_UNIT/INT_PROVINCE_UNIT/EXT_PROVINCE_UNIT. Với comm record, source_id chỉ là source row UUID, không phải selectable ID; client dùng code/sphere. `unresolved` có `{mention_id,raw,kind,evidence,reason,candidates}`; candidates có identity và display name từ registry. `excluded` có `{mention_id,raw,evidence,reason}`. Kết quả không chứa processing/monitoring assignment. INTERNAL_GROUP chỉ xuất thành unit nếu đã xác nhận là node selectable đúng nghĩa; selector tập người phải expand verified membership hoặc unresolved, không biến thành group node để lách việc thiếu danh sách.

### Feedback và health

`POST /v1/outgoing/jobs/{job_id}/feedback` nhận JSON dưới đây và trả HTTP 201 `{feedback_id}`. Identity trong final recipients phải tồn tại trong snapshot đang phản hồi; additions ngoài snapshot phải có verified overlay trước, hoặc ghi như đề xuất chưa resolve trong edits, không thành final ID.

```json
{
  "registry_version": "sha256:registry-with-overlay",
  "alias_policy_version": "sha256:policy",
  "final_recipients": [{"recipient_id": "internal_270", "recipient_type": "INTERNAL_PERSON", "sphere": "internal", "code": "tuanpa@vpub.gialai.gov.vn"}],
  "field_assignments": [{"recipient_id": "internal_270", "field": "save"}],
  "review_decisions": [{"mention_id": "mention-id", "action": "accept_missing", "note": "Văn thư đã kiểm tra"}],
  "edits": [],
  "confirmed": true
}
```

field_assignments optional, field chỉ nhận responsible/save/participants/follow/inside_unit/outside_unit. Review action chỉ nhận resolve/exclude/accept_missing. Decision resolve bắt buộc có `recipient_ids` không rỗng, trỏ tới định danh trong danh sách cuối; exclude/accept_missing giữ danh sách này rỗng và có lý do. Với các lý do toàn cục, `mention_id="reason:<review_reason>"` chỉ nhận accept_missing và phải đúng reason của job. Schema/version sai trả 422/409 có mã lỗi; không diễn giải feedback thành thao tác gửi trên iDesk. Lưu append-only để đánh giá/duyệt rule sau, không tự sửa alias/registry.

`GET /health` trả readiness, provider capabilities/configured, schema version, registry_version và alias_policy_version hiện tại, không trả secret. Client so cả hai version trước fill; khác job thì resolve lại. registry_version cập nhật khi DB/overlay/group membership thay đổi; alias_policy_version cập nhật khi policy thay đổi. Cả hai được theo dõi khi đang chạy, không chỉ khi restart.

## Worker, lưu trữ và cache

Một worker lấy job bằng SQLite transaction và lease. Restart phục hồi queued/lease hết hạn, không để job extracting tồn tại vĩnh viễn. Lưu checkpoint extraction trước resolution. Poll không tạo job mới. Tệp/checkpoint/runtime DB nằm trong var, có cấu hình thời hạn lưu; feedback được giữ theo cấu hình phục vụ đánh giá.

Cache extraction: file hash + extractor/model/prompt version. Cache resolution: extraction hash + issuer/context + registry snapshot + policy + group membership version. resolution_as_of tham chiếu snapshot version, không dùng wall-clock từng giây để vô hiệu cache không cần thiết. Không dùng cache chỉ theo document ID; cùng ID khác file phải khác fingerprint. Failure/OCR thiếu không được cache như result complete.

## Đánh giá và nghiệm thu

Hai gold tách biệt: mention từ PDF và identity hợp lệ theo registry snapshot/policy. Bộ mới nhất phải được rà soát nhãn bị cắt `...`, người bị bỏ sót, duplicate và người soạn/ký không phải nơi nhận. Không lấy toàn bộ proInfos từ crawler làm gold người nhận.

Chia train/rules, validation và holdout theo thời gian; dedupe văn bản/template liên quan giữa các tập. Chạy thêm challenge set viết tắt, nhóm, OCR, đơn vị trùng tên và không có registry. File kết quả lịch sử có thể không đầy đủ; ca chưa annotate đủ được gắn cờ và không nhập nhằng vào mẫu số metric.

Metric chính exact recipient set per document, đo đầu ra backend trước văn thư sửa; kèm precision/recall của ID, extraction recall, registry coverage, auto-resolution/review coverage, unresolved rate, latency và lỗi provider. Ngưỡng nghiệm thu chất lượng là exact set match ≥95% trên holdout khóa có annotation đầy đủ và registry/policy snapshot cố định; 99% là mục tiêu cao hơn. Báo số văn bản/ID được chấm, số ca thiếu annotation, ca lỗi provider và khoảng tin cậy; không âm thầm bỏ ca khó để nâng điểm. Hoàn tất code và test deterministic là mốc MVP kỹ thuật; chưa đạt ngưỡng holdout thì chưa được tuyên bố đạt mục tiêu chất lượng hoặc đủ điều kiện điền hàng loạt không rà soát.

Các fixture bắt buộc: 12355 giữ bốn đơn vị Kính gửi, role Chủ tịch, Lịch, CVP/PVPQT/QTTV và V1/V5/V8; 12349 giữ năm đơn vị và các token Nơi nhận (PDF thực tế là PVPQT); 12418 giữ cả Lịch và Giang dù gold lịch sử thiếu Giang; 12402 giữ selector lãnh đạo/chuyên viên. Mọi ID resolve đều phải tồn tại đúng loại trong registry version.

Test thêm Như trên, Lưu/VT, role nhiều người, staff code đổi cán bộ, tên tắt/Unicode/NFD/khoảng trắng OCR, nhóm đổi membership, đơn vị cùng tên khác sphere/code, người có tên nhưng đã rời registry, PDF scan/hybrid/vùng nhận thiếu, model sinh ID ngoài candidates, invalid JSON/429/timeout, idempotency 409, restart worker và cache invalidation khi policy/registry đổi. Regression deterministic phải pass toàn bộ; score thực tế LLM chỉ công bố sau chạy holdout.

## Dữ liệu cần xác nhận sau

Không cần chờ các xác nhận sau để dựng backend/test offline: portfolio PVPQT/PVPVX/PCVP XD; staff_code mapping hiện tại nếu lookup chưa chứa; membership nhóm; cơ quan đang có trên iDesk nhưng thiếu lookup. Mỗi thiếu dữ liệu có kết quả unresolved rõ ràng. VT trong Lưu không tự map tới cá nhân hoặc tự excluded khi chưa được xác nhận. Không tự thay tên người cũ bằng người mới hoặc sửa DB nguồn để khớp nhãn lịch sử.
