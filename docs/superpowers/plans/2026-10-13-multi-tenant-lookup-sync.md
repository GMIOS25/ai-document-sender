# Multi-Tenant Lookup and Auto-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

This plan implements horizontal multi-tenancy for `ai-document-sender` and automatic background directory synchronization from `Script-Idesk`.

---

## Proposed Changes

### Backend: `ai-document-sender`

#### [config.py](file:///c:/Workspaces/ai-document-sender/src/ai_document_sender/config.py)
- Thêm cấu hình `tenants_dir: Path` và `default_tenant: str = "vpub"`.

#### [tenants.py](file:///c:/Workspaces/ai-document-sender/src/ai_document_sender/tenants.py) (NEW)
- Chuẩn hóa mã tenant (`normalize_tenant_id`).
- Quản lý đường dẫn cơ sở dữ liệu và thư mục của từng tenant (`TenantManager`).
- Cache Registry instances theo tenant ID (`TenantRegistryManager`).

#### [sync.py](file:///c:/Workspaces/ai-document-sender/src/ai_document_sender/sync.py) (NEW)
- Tính mã băm SHA-256 cho `person`, `unit_internal`, `unit_external`.
- So khớp thay đổi (Diff engine): nhận diện thêm (insert), sửa (update), xoá (delete).
- Transactional sync cập nhật các bảng `internal_nodes`, `comm_units`, `recipients`, `recipients_fts`.
- Checkpoint SQLite WAL và cập nhật `metadata.json`.

#### [api.py](file:///c:/Workspaces/ai-document-sender/src/ai_document_sender/api.py)
- Thêm endpoint `POST /v1/sync/lookup`.
- Cập nhật các endpoint `/health`, `/v1/outgoing/jobs`, `/v1/outgoing/recipients/search`, `/v1/outgoing/jobs/{job_id}/feedback` để lấy `Registry` theo `X-Tenant-ID` (fallback về default tenant).

---

### Frontend: `Script-Idesk` (`.worktrees/ban-hanh-van-ban`)

#### [idesk.js](file:///c:/Workspaces/Script-Idesk/.worktrees/ban-hanh-van-ban/src/outgoing/idesk.js)
- Thêm và export hàm `getTenantId()`.

#### [provider.js](file:///c:/Workspaces/Script-Idesk/.worktrees/ban-hanh-van-ban/src/outgoing/provider.js)
- Gửi kèm header `X-Tenant-ID` trong mọi lời gọi API tới backend.
- Thêm phương thức `syncLookup(...)` cho client.

#### [dashboard.js](file:///c:/Workspaces/Script-Idesk/.worktrees/ban-hanh-van-ban/src/outgoing/dashboard.js)
- Kích hoạt cơ chế chạy ngầm tự động định kỳ (tối đa 1 lần/ngày/tenant) khi mở trang văn bản.

---

## Tasks

- [ ] **Task 1: Cấu hình Multi-Tenant & Quản lý Tenant trên Backend**
  - [ ] Thêm `tenants_dir` và `default_tenant` vào `src/ai_document_sender/config.py`.
  - [ ] Viết `src/ai_document_sender/tenants.py` để xử lý đường dẫn, chuẩn hóa tên tenant, quản lý cache `Registry`.
  - [ ] Viết test `tests/test_tenants.py` kiểm tra phân giải tenant, fallback mặc định và quản lý thư mục.
  - [ ] Chạy `pytest tests/test_tenants.py` đảm bảo pass.

- [ ] **Task 2: Xây dựng Smart Sync Diff Engine**
  - [ ] Viết `src/ai_document_sender/sync.py` thực hiện so sánh SHA-256, Diff Thêm/Sửa/Xoá, cập nhật SQLite và FTS5.
  - [ ] Viết test `tests/test_sync.py` kiểm tra:
    - Lần đầu sync: tạo DB và nạp đầy đủ.
    - Lần sau với payload giữ nguyên: trả về `no_change`.
    - Lần sau với payload sửa count/thêm mới/xóa: cập nhật chính xác và FTS5 tìm được bản ghi mới.
  - [ ] Chạy `pytest tests/test_sync.py` đảm bảo pass.

- [ ] **Task 3: Cập nhật API Endpoint & Multi-Tenant Routing**
  - [ ] Thêm endpoint `POST /v1/sync/lookup` trong `src/ai_document_sender/api.py`.
  - [ ] Cập nhật trích xuất `X-Tenant-ID` trong các endpoint hiện hữu.
  - [ ] Viết test `tests/test_api_tenants.py` kiểm tra gọi API với `X-Tenant-ID` khác nhau và endpoint `/v1/sync/lookup`.
  - [ ] Chạy toàn bộ test suite của backend `pytest tests` đảm bảo tất cả tests (bao gồm 110 tests cũ) đều pass.

- [ ] **Task 4: Cập nhật Userscript Outgoing (Script-Idesk)**
  - [ ] Cập nhật `src/outgoing/idesk.js`: export `getTenantId()`.
  - [ ] Cập nhật `src/outgoing/provider.js`: tự động gắn `X-Tenant-ID` và phương thức `syncLookup`.
  - [ ] Cập nhật `src/outgoing/dashboard.js`: thêm tiến trình silent background sync kiểm tra theo ngày.
  - [ ] Cập nhật test `tests/outgoing-provider.test.js`.
  - [ ] Chạy `npm test` và `npm run build:outgoing` trong `.worktrees/ban-hanh-van-ban`.

- [ ] **Task 5: Kiểm chứng Tích hợp End-to-End**
  - [ ] Chạy lệnh kiểm chứng `npm run verify:outgoing` để xác nhận tương thích hoàn toàn.
  - [ ] Thử nghiệm sync thực tế trên tenant mẫu.
  - [ ] Kiểm tra tính toàn vẹn và sạch sẽ của mã nguồn.
