# Thiết kế Kỹ thuật: Hệ thống Multi-Tenant Lookup & Đồng bộ Tự động Danh bạ iDesk

- **Ngày ban hành**: 2026-10-13
- **Trạng thái**: Đã phê duyệt (Approved)
- **Phạm vi**: `ai-document-sender` (Backend) & `Script-Idesk` (`.worktrees/ban-hanh-van-ban`, Outgoing Userscript)

---

## 1. Bối cảnh & Mục tiêu

### 1.1. Bối cảnh
Hệ thống hiện tại lưu trữ dữ liệu tra cứu nơi nhận / người nhận văn bản trong một file SQLite đơn nhất `resources/data/lookup.db` được tạo từ 3 tệp JSON (`person.json`, `unit_internal_province.json`, `unit_except_provice.json`).
Khi người dùng làm việc trên nhiều hệ thống iDesk của các cơ quan, đơn vị khác nhau (ví dụ: Văn phòng UBND tỉnh `vpub`, Sở Nông nghiệp & Môi trường `snnmt`, các tỉnh/thành phố khác), cơ cấu tổ chức và danh mục liên thông là hoàn toàn khác nhau nhưng cùng dùng chung một cấu trúc API iDesk. Đồng thời, việc cập nhật danh bạ hiện tại phụ thuộc vào việc bật DevTools copy/paste thủ công.

### 1.2. Mục tiêu
1. **Mở rộng theo chiều ngang (Horizontal Scaling & Multi-Tenancy)**: Hỗ trợ nhiều khách hàng (tenants), mỗi khách hàng sở hữu cơ sở dữ liệu tra cứu (`lookup.db`) độc lập (Database-per-Tenant) với đầy đủ cách ly dữ liệu.
2. **Tenant Resolution**: Tự động nhận diện tenant thông qua tiền tố đường dẫn URL của iDesk (`/vpub/`, `/snnmt/`...) và gửi qua header `X-Tenant-ID`. Tương thích ngược 100% với cấu hình và test suite hiện có thông qua default tenant (`vpub`).
3. **Smart Sync & Diff Engine**: Cung cấp endpoint `POST /v1/sync/lookup` cho phép kiểm tra hash SHA-256 nhanh (<5ms) và thực hiện thêm, sửa, xoá (Upsert & Delete) vào SQLite `lookup.db` kèm chỉ mục FTS5.
4. **Tự động chạy ngầm trên Userscript**: `Script-Idesk` tự động kiểm tra định kỳ (tối đa 1 lần/ngày/phiên làm việc) khi người dùng mở trang "Ban hành văn bản", âm thầm gọi 3 API của iDesk và đẩy về backend mà không gián đoạn thao tác của người dùng.

---

## 2. Kiến trúc Hệ thống

```
+---------------------------------------------------------------------------------+
|                                 iDesk Web Client                                |
|  https://vpdt.gialai.gov.vn/{tenant_id}/smartcloud/idesk6/...                   |
|                                                                                 |
|  [Script-Idesk Userscript (dist/idesk_outgoing.user.js)]                        |
|   1. getTenantId() -> Trích xuất tenant_id từ pathname (/vpub/, /snnmt/)        |
|   2. Background Checker: Kiểm tra last_sync_${tenant_id}                        |
|   3. Gọi 3 API iDesk (với session cookie hiện có):                              |
|      - POST .../comm/nodes/fbyvsphere.cpx                                       |
|      - GET  .../history/organext/list.cpx?sphere=int_province_comm               |
|      - GET  .../history/organext/list.cpx?sphere=ext_province_comm               |
+---------------------------------------+-----------------------------------------+
                                        | POST /v1/sync/lookup
                                        | Header: X-Tenant-ID: {tenant_id}
                                        | Header: X-API-Key: {api_key}
                                        v
+---------------------------------------------------------------------------------+
|                        FastAPI Backend (ai-document-sender)                     |
|                                                                                 |
|  [Tenant Middleware / Dependency]:                                              |
|   - Trích xuất & chuẩn hóa `X-Tenant-ID` (fallback 'vpub')                     |
|                                                                                 |
|  [Tenant Registry Manager]:                                                     |
|   - Quản lý Registry snapshot & connection pool theo tenant_id                  |
|                                                                                 |
|  [Smart Sync Diff Engine]:                                                      |
|   1. Fast SHA-256 Hash Check vs resources/tenants/{tenant_id}/metadata.json     |
|   2. Nếu đổi: Transaction Diff (INSERT mới, UPDATE sửa, DELETE cũ)             |
|   3. Cập nhật FTS5 Virtual Table (recipients_fts)                               |
|   4. Lưu snapshot JSON & PRAGMA wal_checkpoint(TRUNCATE)                        |
|   5. Invalidate / Reload Tenant Registry Cache                                  |
+---------------------------------------+-----------------------------------------+
                                        v
                          [Thư mục lưu trữ theo Tenant]
                           resources/tenants/{tenant_id}/
                           ├── lookup.db
                           ├── person.json
                           ├── unit_internal_province.json
                           ├── unit_except_provice.json
                           └── metadata.json
```

---

## 3. Đặc tả Chi tiết Backend (`ai-document-sender`)

### 3.1. Cấu trúc thư mục dữ liệu
- Mặc định/Legacy: `resources/data/lookup.db` vẫn tồn tại để làm fallback cho các test suite và môi trường đơn giản.
- Thư mục Multi-Tenant: `resources/tenants/{tenant_id}/`.
- Khi khởi động hoặc khi nhận request với `tenant_id`:
  - Nếu `resources/tenants/{tenant_id}/lookup.db` chưa tồn tại nhưng `tenant_id == "vpub"` và `resources/data/lookup.db` tồn tại, hệ thống tự động copy/khởi tạo tenant `vpub` từ `resources/data/`.
  - Nếu thư mục tenant chưa có DB, hệ thống có thể tạo DB rỗng hoặc nạp từ payload đồng bộ đầu tiên.

### 3.2. Cấu hình (`Settings`)
Bổ sung trong `src/ai_document_sender/config.py`:
- `tenants_dir: Path = ROOT / "resources/tenants"`
- `default_tenant: str = "vpub"`

### 3.3. Tenant Resolution & Tenant Registry Manager
Bổ sung module `src/ai_document_sender/tenants.py`:
- `normalize_tenant_id(raw: str | None) -> str`:
  - Loại bỏ ký tự không an toàn: `re.sub(r"[^a-z0-9_-]", "", (raw or "").strip().lower())`.
  - Fallback về `settings.default_tenant` nếu rỗng.
- `TenantManager`:
  - `get_tenant_dir(tenant_id: str) -> Path`
  - `get_db_path(tenant_id: str) -> Path`
  - `get_registry(tenant_id: str) -> Registry` (kèm in-memory cache có TTL hoặc reload khi sync).
  - `invalidate_registry(tenant_id: str) -> None`

### 3.4. Module Smart Sync (`src/ai_document_sender/sync.py`)
- Hàm `sync_tenant_lookup(tenant_id: str, payload: dict, settings: Settings) -> dict`:
  1. **Tính SHA-256**:
     - `person_hash = sha256(payload.get("person"))`
     - `unit_int_hash = sha256(payload.get("unit_internal"))`
     - `unit_ext_hash = sha256(payload.get("unit_external"))`
     - So sánh với `metadata.json` trong thư mục tenant. Nếu khớp toàn bộ ➔ trả về `{"status": "no_change", "tenant_id": tenant_id}`.
  2. **Thực thi Diff & Upsert/Delete**:
     - Tạo hoặc mở kết nối SQLite tới `resources/tenants/{tenant_id}/lookup.db`.
     - Thực thi trong Transaction (`BEGIN TRANSACTION`):
       - Khử trùng lặp `comm_units` nội tỉnh và ngoại tỉnh dựa trên `code` (lấy count lớn nhất).
       - Đối chiếu với DB hiện tại:
         + Xác định tập cần `INSERT` (mã mới).
         + Xác định tập cần `UPDATE` (mã cũ nhưng `name`, `count`, `organ_id`... thay đổi).
         + Xác định tập cần `DELETE` (mã có trong DB nhưng không còn trong API mới).
       - Tương tự đối với `internal_nodes`:
         + So khớp theo `id` số của từng node.
       - Tái tạo / cập nhật bảng `recipients` và bảng chỉ mục `recipients_fts`.
     - Chạy `PRAGMA wal_checkpoint(TRUNCATE);`.
  3. **Lưu trữ Snapshot & Metadata**:
     - Lưu 3 file JSON vào `resources/tenants/{tenant_id}/`.
     - Cập nhật `metadata.json` chứa các hash mới, `last_synced_at`, `record_counts`.
  4. **Làm mới Cache**:
     - Gọi `tenant_manager.invalidate_registry(tenant_id)`.

### 3.5. Cập nhật API Endpoints (`src/ai_document_sender/api.py`)
- Endpoint mới: `POST /v1/sync/lookup`
  - Nhận `X-Tenant-ID` header và `X-API-Key` (nếu cấu hình).
  - Body: JSON chứa `{"person": ..., "unit_internal": ..., "unit_external": ...}`.
  - Gọi `sync_tenant_lookup`.
- Các Endpoint hiện hữu:
  - `/health`: Bổ sung tenant information trong kết quả trả về khi có `X-Tenant-ID`.
  - `/v1/outgoing/jobs`: Lấy `current_registry(tenant_id)` thay vì registry tĩnh. Job lưu snapshot tương ứng của tenant đó.
  - `/v1/outgoing/recipients/search`: Tra cứu trên `current_registry(tenant_id)`.
  - `/v1/outgoing/jobs/{job_id}/feedback`: Xác thực trên `current_registry(tenant_id)`.

---

## 4. Đặc tả Chi tiết Phía Userscript (`Script-Idesk`)

Worktree: `C:\Workspaces\Script-Idesk\.worktrees\ban-hanh-van-ban`

### 4.1. Nhận diện Tenant (`src/outgoing/idesk.js`)
- Hàm `getTenantId()`:
  ```javascript
  export const getTenantId = () => {
      const match = window.location.pathname.match(/^\/([^/]+)\/smartcloud/);
      return match ? match[1].toLowerCase() : 'vpub';
  };
  ```

### 4.2. Header `X-Tenant-ID` (`src/outgoing/provider.js`)
- Trong `createSenderClient`:
  - Tự động gắn header `X-Tenant-ID: getTenantId()` trong hàm `call()` cho tất cả các request gửi sang backend.
  - Bổ sung phương thức `syncLookup({ person, unit_internal, unit_external })` gửi tới `POST /v1/sync/lookup`.

### 4.3. Tự động kiểm tra & Chạy ngầm (`src/outgoing/dashboard.js` hoặc module đồng bộ riêng)
- Lưu key trạng thái: `idesk_last_sync_${tenantId}` trong `GM_getValue`/`GM_setValue`.
- Khi trang `publish-doc.cpx` sẵn sàng và bắt được `exeacode` phiên làm việc:
  - Kiểm tra `today = new Date().toISOString().slice(0, 10)`.
  - Nếu `lastSync !== today`:
    - Chạy ngầm trong `setTimeout(..., 1000)`:
      - Gọi 3 API: `ENDPOINTS.internal`, `ENDPOINTS.organization` (int và ext) bằng `fetchJson`.
      - Gửi `client.syncLookup(...)`.
      - Khi hoàn thành thành công: Ghi nhận `GM_setValue(syncKey, today)`.
      - Bắt lỗi âm thầm (silent fail, không alert lỗi ra UI để tránh làm phiền người dùng nếu backend chưa bật).

---

## 5. Kế hoạch Kiểm thử & Đảm bảo Chất lượng

1. **Unit & Integration Tests trong `ai-document-sender`**:
   - Kiểm tra trích xuất `X-Tenant-ID` (hợp lệ, không hợp lệ, thiếu header ➔ fallback `vpub`).
   - Kiểm tra `POST /v1/sync/lookup`:
     - Gửi lần 1: tạo DB tenant mới, trả về `synced`.
     - Gửi lại nguyên vẹn: trả về `no_change`.
     - Gửi thay đổi (thêm đơn vị, sửa count, xóa đơn vị): DB cập nhật đúng số lượng, FTS5 tìm được đơn vị mới.
   - Kiểm tra cách ly dữ liệu giữa 2 tenant (`vpub` vs `snnmt`).
   - Kiểm tra toàn bộ 110 tests hiện tại tiếp tục vượt qua (không có hồi quy).
2. **Kiểm thử trong `Script-Idesk`**:
   - Unit tests cho `getTenantId()` và header `X-Tenant-ID` trong `provider.js`.
   - Build bundle `npm run build:outgoing`.
   - Chạy `npm test` trong worktree outgoing.
