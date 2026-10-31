# Báo Cáo Tổng Hợp Các Dòng Chưa Ánh Xạ Nơi Nhận 2 ('-')

> **Tài liệu tham chiếu**: `ORIGINAL_REQUEST.md` (Yêu cầu R4)
> **Bảng tính mục tiêu**: `1FTx3IDxfaOadbXmY6BB9pRkRqCdnCter12poQ1txu9s`, Tab `Thống kê`
> **Thời gian khởi tạo**: 2026-10-31 03:32:01Z

---

## 1. Tóm Tắt Tổng Quan (Executive Summary)

- **Tổng số dòng chưa ánh xạ ban đầu ('-')**: 907 dòng.
- **Số dòng đã được chuẩn hóa và cập nhật thành công (Chữ đỏ #FF0000)**: 81 dòng.
- **Số dòng bảo lưu giá trị '-' theo quy chuẩn**: **826 dòng**.

### Phân Loại Các Dòng Bảo Lưu Giá Trị '-':

| STT | Phân Nhóm Nguyên Nhân | Mã Phân Loại | Số Lượng Dòng | Tỷ Lệ | Đề Xuất Xử Lý Văn Thư |
|---|---|---|---|---|---|
| 1 | Ký hiệu Lưu trữ Văn thư (VT) | `POLICY_ARCHIVAL_VT` | **474** | 57.4% | Giữ nguyên `-`. Đây là nơi lưu hồ sơ văn thư nội bộ, không gửi ra ngoài. |
| 2 | Ký hiệu Chuyên viên / Phòng ban Soạn thảo (Lưu: VT, ...) | `INTERNAL_FILING_OR_SPECIALIST_CODE` | **44** | 5.3% | Giữ nguyên `-`. Ký hiệu lưu bản cứng chuyên viên phụ trách, không gửi qua trục điện tử. |
| 3 | Cơ quan Đảng / Thường trực Tỉnh ủy (Kênh gửi mật / Bản giấy) | `PARTY_COMMITTEE_CHANNEL` | **52** | 6.3% | Giữ nguyên `-`. Đơn vị thuộc hệ thống Đảng, phát hành qua kênh bảo mật/bản giấy riêng. |
| 4 | Đối tượng tổng hợp, cá nhân công dân hoặc 'Như trên' | `COMPOSITE_OR_INDIVIDUAL` | **132** | 16.0% | Cần cán bộ văn thư rà soát thủ công danh sách chi tiết kèm theo văn bản chính. |
| 5 | Đơn vị ngoài tỉnh / Doanh nghiệp chưa có mã e-document | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | **124** | 15.0% | Cần đăng ký bổ sung mã định danh trục liên thông e-document hoặc gửi bưu chính. |

---

## 2. Chi Tiết Từng Nhóm Nguyên Nhân & Căn Cứ Xử Lý

### 2.1 Nhóm Ký Hiệu Lưu Trữ Văn Thư (`VT` - 474 dòng)
- **Căn cứ thực tế**: Trong 1.498 dòng được cán bộ văn thư sửa thủ công trước đó, giá trị `VT` **không bao giờ được gán nơi nhận** (tỷ lệ 0%).
- **Bản chất nghiệp vụ**: `VT` là viết tắt của 'Lưu: Văn thư' theo Nghị định 30/2020/NĐ-CP về công tác văn thư. Đây là bản lưu hồ sơ tại văn thư cơ quan, không phải cơ quan/đơn vị nhận văn bản phát hành.
- **Chính sách hệ thống**: Đã được định nghĩa trong `resources/policies/recipient_aliases.v1.json` trạng thái `pending` (nội bộ).
- **Kết luận**: Bảo lưu tuyệt đối giá trị `-` cho toàn bộ 474 dòng.

### 2.2 Nhóm Ký Hiệu Lưu Chuyên Viên & Phòng Soạn Thảo (44 dòng)
- **Ví dụ điển hình**: `Lưu: VT, BTCD`, `Lưu: VT, HSVV-TD`, `Lưu: VT, TM`, `Lưu: VT, C4`, `Lưu: VT, N1`.
- **Bản chất nghiệp vụ**: Phần ghi chú nơi lưu nội bộ cho chuyên viên/bộ phận chuyên môn theo dõi hồ sơ vụ việc.
- **Kết luận**: Bảo lưu `-` vì không đại diện cho điểm đến gửi đi.

### 2.3 Nhóm Cơ Quan Đảng & Kênh Bảo Mật (52 dòng)
- **Ví dụ điển hình**: `Thường trực Tỉnh ủy`, `Ban Tổ chức Tỉnh ủy`, `Ban Tuyên giáo Tỉnh ủy`.
- **Bản chất nghiệp vụ**: Các cơ quan lãnh đạo/chỉ đạo cấp ủy Đảng (như Ban Thường vụ, Thường trực Tỉnh ủy, các ban đảng) nhận văn bản chỉ đạo qua hệ thống bảo mật chuyên dùng hoặc văn bản giấy niêm phong, không thuộc diện gửi công khai qua VDX hành chính nhà nước. Riêng cơ quan hành chính của Đảng đã đăng ký mã định danh chính thức (`Đảng ủy Ủy ban nhân dân tỉnh Gia Lai`) hoặc phân phối đồng gửi liên cơ quan (`Văn phòng Tỉnh ủy;Văn phòng Đoàn ĐBQH và HĐND tỉnh Gia Lai`) đã được chuẩn hóa ánh xạ khi có căn cứ gửi đi thực tế.
- **Kết luận**: Giữ `-` đối với các ban đảng và cơ quan lãnh đạo trực thuộc Tỉnh ủy trên hệ thống gửi e-document, chuyển văn bản giấy/kênh bảo mật.

### 2.4 Nhóm Đối Tượng Tổng Hợp & Cá Nhân Công Dân (132 dòng)
- **Ví dụ điển hình**: `Bí thư Đảng ủy, Chủ tịch UBND các xã, phường nơi có dự án điện 1`, `Chủ đầu tư các dự án điện trên địa bàn tỉnh`, `Ông Nguyễn Văn Thanh (để biết)`, `Như trên`.
- **Bản chất nghiệp vụ**: Các danh sách gộp nhiều đối tượng hoặc địa chỉ cá nhân người dân không có mã định danh định tuyến tự động trên hệ thống danh mục điện tử.
- **Kết luận**: Giữ `-`, yêu cầu văn thư rà soát danh sách đính kèm trong phụ lục văn bản để phát hành thủ công.

### 2.5 Nhóm Đơn Vị Trung Ương & Doanh Nghiệp Ngoài Tỉnh (124 dòng)
- **Ví dụ điển hình**: `Viện Sinh thái Nhiệt đới`, `Công ty TNHH MTV Cà phê Ia Blan`, `Công ty CP Tập đoàn FLC`, `Cảng Hàng không Pleiku`, `Truyền tải điện 3`.
- **Bản chất nghiệp vụ**: Đơn vị ngoài tỉnh hoặc doanh nghiệp chưa tích hợp trục gửi liên thông điện tử của tỉnh Gia Lai. Điển hình dòng 805 `Truyền tải điện 3` (PTC3 trực thuộc EVNNPT) là doanh nghiệp truyền tải điện lưới quốc gia, không có điểm tích hợp gửi nhận văn bản trên trục nội tỉnh (văn bản cùng số hiệu đã gửi Công ty Điện lực Gia Lai tại dòng 804).
- **Kết luận**: Giữ `-`, chuyển bộ phận bưu chính phát hành văn bản giấy có ký số xác thực.

---

## 3. Danh Mục Chi Tiết Toàn Bộ 826 Dòng Bảo Lưu '-' (Clerical Review Log)

| Dòng | Số Hiệu Văn Bản | Nơi Nhận 1 (Trích Xuất Thô) | Phân Nhóm | Ghi Chú & Đề Xuất Cán Bộ Văn Thư |
|---|---|---|---|---|
| 14 | `13116/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 25 | `13115/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 32 | `13114/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 42 | `13110/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 50 | `13109/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 58 | `13108/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 67 | `13107/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 73 | `13104/UBND-XDCT` | Bí thư Đảng ủy, Chủ tịch UBND các xã, phường nơi có dự án điện 1 | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 74 | `13104/UBND-XDCT` | Chủ đầu tư các dự án điện trên địa bàn tỉnh2 | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 81 | `13104/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 89 | `13103/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 101 | `13102/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 109 | `13101/UBND-NNMT` | Thường trực HDND tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 117 | `13101/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 125 | `13100/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 136 | `13099/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 145 | `13098/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 158 | `13097/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 174 | `13096/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 178 | `13095/UBND-NC` | Các Sở, ngành tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 179 | `13095/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 180 | `13095/UBND-NC` | Các cơ quan tham mưu, giúp việc của Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 183 | `13095/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 192 | `13094/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 204 | `13093/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 208 | `13092/UBND-XDCT` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 219 | `13092/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 226 | `13091/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 230 | `13090/UBND-NC` | Cục Dân vận/Tổng cục Chính trị QĐND Việt Nam | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 235 | `13090/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 244 | `13089/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 252 | `13088/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 263 | `13087/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 272 | `13086/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 277 | `13085/UBND-KGVX` | Thường trực Tỉnh ủy (để b/c) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 284 | `13085/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 299 | `13084/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 304 | `13083/UBND-KGVX` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 312 | `13083/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 322 | `13082/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 327 | `13081/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 339 | `13080/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 349 | `13079/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 357 | `13078/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 373 | `13077/UBND-NNMT` | Công ty TNHH Đầu tư hạ tầng Khu công nghiệp Nhơn Hòa | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 374 | `13077/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 383 | `13076/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 387 | `13075/UBND-KTTH` | Các thành viên Ban Chỉ đạo phục vụ tổ chức Hội nghị ISOM – APEC 2027 tại Gia Lai | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 392 | `13075/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 402 | `13074/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 413 | `13073/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 415 | `13073/UBND-NNMT` | Ngu | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, Ngu'). |
| 425 | `13072/UBND-XDCT` | Công ty CP Đầu tư và Xây dựng Bình Định | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 430 | `13072/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 432 | `13071/UBND-NNMT` | Ngân hàng Tái thiết Đức (KfW) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 441 | `13071/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 449 | `13070/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 461 | `13069/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 463 | `13068/UBND-NNMT` | Đồng chí Phó Thủ tướng Chính phủ Hồ Quốc Dũng Ủy ban nhân dân tỉnh Gia Lai trân trọng cảm ơn sự quan tâm, chỉ đạo của Chính phủ, Thủ tướng Chính phủ và Phó Thủ tướng Chính phủ đối với công tác hoàn thiện cơ sở dữ liệu đất đai trên địa bàn tỉnh. Để tiếp tục triển khai thực hiện, Ủy ban nhân dân tỉnh kính báo cáo và đề xuất Phó Thủ tướng Chính phủ một số nội dung sau: 1. Thông tin chung về Dự án: | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 474 | `13068/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 486 | `13066/UBND-XDCT` | Chủ đầu tư các cụm công nghiệp trên địa bàn tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 492 | `13066/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 501 | `13065/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 507 | `13064/UBND-NNMT` | Công ty TNHH Trái cây Đỉnh Phong | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 510 | `13064/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 520 | `13063/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 522 | `13063/UBND-XDCT` | tr | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 524 | `13062/UBND-XDCT` | Công ty cổ phần Tập đoàn Đức Long Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 530 | `13062/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 543 | `13061/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 549 | `13060/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 560 | `13059/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 569 | `13058/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 575 | `13057/UBND-NNMT` | Văn phòng đại diện Stichting IDH tại Việt Nam | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 580 | `13057/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 588 | `13056/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 591 | `13055/UBND-NC` | Cục Dân quân tự vệ | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 596 | `13055/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 606 | `13054/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 614 | `13053/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 623 | `13052/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 632 | `13051/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 634 | `13051/UBND-KGVX` | Văn bản số 10139/STC-QLGCS ngày 06/10/2026 và Văn bản số 1 1 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 642 | `13050/UBND-NNMT` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 644 | `13050/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 647 | `13049/UBND-NNMT` | Quỹ Phòng, chống thiên tai tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 654 | `13049/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 657 | `13048/UBND-KTTH` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 663 | `13048/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 669 | `13047/UBND-KTTH` | Viện Sinh thái Nhiệt đới | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 674 | `13047/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 682 | `13046/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 693 | `13045/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 698 | `13044/UBND-KTTH` | Các doanh nghiệp nhà nước do UBND tỉnh làm đại diện chủ sở hữu | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 703 | `13044/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 713 | `13043/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 721 | `13042/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 736 | `13041/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 740 | `13040/UBND-KGVX` | Ủy ban nhân dân các tỉnh, thành phố trực thuộc Trung ương | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 741 | `13040/UBND-KGVX` | Thường trực Tỉnh ủy (b/c) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 748 | `13040/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 760 | `13039/UBND-TD` | Ông Trần Văn Lắm (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 761 | `13039/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 772 | `13037/UBND-KGVX` | VT, V1, V5, V8 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 774 | `13037/UBND-KGVX` | Thường trực Tỉnh ủy (thay báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 779 | `13037/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 789 | `13036/UBND-NNMT` | Công ty CP Sơn Hải | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 792 | `13036/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 805 | `13035/UBND-XDCT` | Truyền tải điện 3 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | PTC3 - Công ty Truyền tải điện 3 trực thuộc EVNNPT là doanh nghiệp truyền tải quốc gia, chưa tích hợp mã định danh trên trục liên thông văn bản tỉnh Gia Lai; văn bản đã gửi Công ty Điện lực Gia Lai tại dòng 804 |
| 806 | `13035/UBND-XDCT` | Các Ban QLDA gửi Văn bản này cho các nhà thầu thi công; Ng | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 809 | `13035/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 812 | `13034/UBND-KGVX` | Các sở ban ngành và đơn vị thuộc tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 817 | `13034/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 823 | `13033/UBND-NNMT` | Công ty TNHH Sơn Thạch | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 827 | `13033/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 830 | `13032/UBND-NNMT` | Công ty TNHH MTV Dịch vụ khai thác Hải sản Biển Đông | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 835 | `13032/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 845 | `13031/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 853 | `13030/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 859 | `13028/UBND-KGVX` | Lưu: VT, V1, N2, V5, V8. | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 863 | `13028/UBND-KGVX` | Hội Sinh vật cảnh tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 864 | `13028/UBND-KGVX` | Công ty TNHH Xúc tiến thương mại-Quảng cáo Sinh vật cảnh PVC | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 869 | `13028/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 874 | `13027/UBND-TD` | Bà Nguyễn Thị Hương Địa chỉ: Số 434/34/7A Bình Quới, phường Bình Quới, thành phố Hồ Chí Minh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 883 | `13027/UBND-TD` | CVP và PVP-TH (b/c); N | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 885 | `13027/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 886 | `13027/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 895 | `13026/UBND-NC` | Các cơ quan TW đóng trên địa bàn tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 899 | `13026/UBND-NC` | Công ty TNHH KTCTTL Bình Định; Ng | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 902 | `13026/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 913 | `13025/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 924 | `13024/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 935 | `13023/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 949 | `13022/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 959 | `13021/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 962 | `13020/UBND-NC` | Các đơn vị sự nghiệp công lập thuộc UBND tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 968 | `13020/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 973 | `13019/UBND-KGVX` | Bảo tàng Pleiku | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 978 | `13019/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 990 | `13018/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 999 | `13017/UBND-XDCT` | Công ty cổ phần Tập đoàn FLC | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1006 | `13017/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1018 | `13016/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1027 | `13015/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1033 | `13014/UBND-NNMT` | Các tổ chức chính trị - xã hội | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1036 | `13014/UBND-NNMT` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1042 | `13014/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1048 | `13013/UBND-NC` | Ban Trị sự Giáo hội Phật giáo Việt Nam tỉnh Gia Lai | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1057 | `13013/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1061 | `13012/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1066 | `13012/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1076 | `13011/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1081 | `13010/UBND-XDCT` | Công ty cổ phần Năng lượng VinEnergo | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1088 | `13010/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1091 | `13009/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1098 | `13009/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1110 | `13008/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1113 | `13008/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 1114 | `13007/UBND-KTTH` | Tiểu ban Lễ tân - Ủy ban Quốc gia APEC 2027 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1115 | `13007/UBND-KTTH` | Tiểu ban An ninh - Y tế - Ủy ban QG APEC 2027 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1118 | `13007/UBND-KTTH` | Thành viên BCĐ PVHN (ISOM) APEC 2027 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1122 | `13007/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1126 | `13006/UBND-NNMT` | Công ty Cổ phần Hoàng Anh Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1131 | `13006/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1135 | `13005/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1142 | `13005/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1151 | `13004/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1160 | `13002/UBND-NC` | Cơ quan Cảnh sát điều tra Công an tỉnh Tuyên Quang | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1162 | `13002/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1175 | `13001/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1183 | `13000/UBND-XDCT` | Công ty TNHH Thiên Hưng Mỹ Thọ | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1188 | `13000/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1198 | `12999/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1200 | `12998/UBND-KGVX` | Cơ quan Cảnh sát điều tra Công an Thành phố Hồ Chí Minh Phúc đáp Văn bản số C60616/YC-CSKT ngày 05/10/2026 của Cơ quan Cảnh sát điều tra Công an Thành phố Hồ Chí Minh về việc yêu cầu cung cấp chứng cứ, đồ vật, tài liệu, dữ liệu điện tử liên quan đến Công ty Cổ phần Redeyes và bà Thái Thị Thu Đào; trên cơ sở kết quả rà soát theo Công văn số 12726/UBND-KGVX ngày 15/10/2026 của UBND tỉnh, UBND tỉnh Gia Lai cung cấp thông tin, tài liệu như sau: 1. Về kết quả rà soát, xử lý hồ sơ Qua rà soát hồ sơ, tài liệu từ năm 2023 đến nay, UBND tỉnh có tiếp nhận Văn bản số 09/2026/CV-REDEYES của Công ty Cổ phần Redeyes về việc đề xuất phối hợp triển khai chương trình phát triển cộng đồng. Ngày 11/6/2026, UBND tỉnh ban hành Công văn số 7829/UBND-KGVX giao Sở Văn hóa, Thể thao và Du lịch nghiên cứu, xử lý theo thẩm quyền. Ngày 18/6/2026, Sở Văn hóa, Thể thao và Du lịch ban hành Công văn số 2653/SVHTTDL-QLPTDL đề nghị Công ty bổ sung hồ sơ, tài liệu; tuy nhiên, Công ty không bổ sung theo yêu cầu nên không phát sinh việc xem xét, xử lý các thủ tục tiếp theo liên quan đến đề xuất của Công ty | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1205 | `12998/UBND-KGVX` | Phòng KGVX – VP UBND tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1206 | `12998/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1216 | `12997/UBND-KGVX` | Tiểu ban Lễ tân - Hậu cần - Vận động tài trợ (theo Quyết định số 228/QĐ-BTC ngày 12/10/2026 của BTC) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1219 | `12997/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1226 | `12996/UBND-NNMT` | Công ty CP Tập đoàn Đức Long Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1231 | `12996/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1239 | `12995/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1248 | `12994/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1262 | `12993/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1271 | `12992/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1282 | `12991/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1293 | `12990/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1303 | `12989/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1311 | `12988/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1341 | `12987/UBND-XDCT` | Công ty CP Đường sắt Nghĩa Bình, Phú Khánh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1346 | `12987/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1349 | `12986/UBND-NC` | T M | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, T M'). |
| 1355 | `12986/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1363 | `12985/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1364 | `12985/UBND-TD` | HSVV-TD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, HSVV-TD'). |
| 1374 | `12984/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1385 | `12983/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1395 | `12982/UBND-TD` | Ông Nguyễn Văn Thanh (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1396 | `12982/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1399 | `12981/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1404 | `12981/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1419 | `12980/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1427 | `12979/UBND-XDCT` | TT Tỉnh ủy (báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1440 | `12979/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1446 | `12978/UBND-XDCT` | Công ty TNHH Đầu tư Phú Tài Diêu Trì | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1451 | `12978/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1458 | `12977/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1465 | `12976/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1470 | `12975/UBND-KTTH` | Công ty cổ phần Diên Hồng Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1475 | `12975/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1485 | `12974/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1493 | `12973/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1505 | `12972/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1509 | `12971/UBND-NNMT` | Bà Nguyễn Thị Liễu | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1517 | `12971/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1523 | `12970/UBND-NNMT` | Công ty cổ phần du lịch Xuân Thủy | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1528 | `12970/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1537 | `12969/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1550 | `12967/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1563 | `12966/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1572 | `12965/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1578 | `12964/UBND-NC` | Đ/c Nguyễn Ngọc Lương, Phó Bí thư Tỉnh ủy, Chủ tịch Ủy ban Mặt trận Tổ quốc Việt Nam tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1583 | `12964/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1591 | `12963/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1603 | `12962/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1612 | `12961/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1615 | `12960/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1620 | `12960/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1623 | `12959/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1629 | `12959/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1634 | `12958/UBND-NC` | Các doanh nghiệp nhà nước | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1635 | `12958/UBND-NC` | Các đơn vị sự nghiệp công lập thuộc tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1636 | `12958/UBND-NC` | Các doanh nghiệp, tổ chức khu vực ngoài Nhà nước | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1637 | `12958/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1641 | `12958/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1643 | `12958/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1652 | `12957/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1663 | `12956/UBND-XDCT` | Trạm Kiểm dịch thực vật Cửa khẩu quốc tế Lệ Thanh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1668 | `12956/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1677 | `12955/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1686 | `12954/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1697 | `12953/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1706 | `12952/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1713 | `12951/UBND-NNMT` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 1716 | `12951/UBND-NNMT` | Cty Cổ phần Thác Bà Lake | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1717 | `12951/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1718 | `12951/UBND-NNMT` | N X | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N X'). |
| 1726 | `12950/UBND-TD` | Ông Trần Văn Toàn (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1728 | `12950/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1738 | `12949/UBND-XDCT` | PVP | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1741 | `12949/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1750 | `12948/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1751 | `12948/UBND-NNMT` | N , , X | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N , , X'). |
| 1758 | `12947/UBND-XDCT` | Công ty TNHH Dịch vụ du lịch Quốc Thắng | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1763 | `12947/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1765 | `12946/UBND-KGVX` | Ông DANG CO-MINH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1768 | `12946/UBND-KGVX` | ĐSQ Pháp tại Việt Nam (để biết) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1769 | `12946/UBND-KGVX` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1772 | `12946/UBND-KGVX` | NgV | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, NgV'). |
| 1782 | `12945/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1787 | `12944/UBND-KGVX` | Công ty TNHH K.T.L | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1791 | `12944/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1794 | `12943/UBND-KTTH` | Vụ NSNN (Bộ Tài chính) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1800 | `12943/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1810 | `12942/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1812 | `12941/UBND-KGVX` | Hiệp hội Văn hóa Ẩm thực Việt Nam (VCCA) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1813 | `12941/UBND-KGVX` | Liên Chi hội Văn hoá Chè Việt Nam | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1814 | `12941/UBND-KGVX` | Liên Chi hội Phở | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1815 | `12941/UBND-KGVX` | M | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, M'). |
| 1816 | `12941/UBND-KGVX` | TT Tỉnh uỷ | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1817 | `12941/UBND-KGVX` | BTV Đảng uỷ UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1821 | `12941/UBND-KGVX` | HHVHAT tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1824 | `12941/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1827 | `12940/UBND-KGVX` | Hiệp hội Văn hóa Ẩm thực Việt Nam (VCCA) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1828 | `12940/UBND-KGVX` | M | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, M'). |
| 1829 | `12940/UBND-KGVX` | TT Tỉnh uỷ | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1830 | `12940/UBND-KGVX` | BTV Đảng uỷ UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1834 | `12940/UBND-KGVX` | HHVHAT tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1837 | `12940/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1844 | `12939/UBND-KTTH` | Các đơn vị trong Ban Chỉ đạo phục vụ tổ chức Hội nghị Quan chức cao cấp không chính thức (ISOM) APEC 2027 tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1849 | `12939/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1854 | `12938/UBND-KGVX` | Thường trực Tỉnh ủy (báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1855 | `12938/UBND-KGVX` | Thường trực HĐND tỉnh (báo cáo) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1862 | `12938/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1874 | `12937/UBND-TD` | Bà Trương Thị Bụt (để biết) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1876 | `12937/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1885 | `12936/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1894 | `12935/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1895 | `12935/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 1903 | `12934/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1916 | `12933/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1922 | `12932/UBND-KTTH` | Viện Sinh thái Nhiệt đới | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1927 | `12932/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1935 | `12931/UBND-KGVX` | Ban VH-XH, HĐND tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 1946 | `12930/UBND-NC` | Bộ Công an (V01) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 1947 | `12930/UBND-NC` | TT. Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 1951 | `12930/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1961 | `12929/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1974 | `12928/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1983 | `12927/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1989 | `12926/UBND-NNMT` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 1992 | `12926/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 1993 | `12926/UBND-NNMT` | N X | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N X'). |
| 2002 | `12925/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2012 | `12924/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2017 | `12923/UBND-NC` | Hiệp hội Doanh nghiệp tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2022 | `12923/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2028 | `12922/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2030 | `12922/UBND-NNMT` | Như trên | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2038 | `12921/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2040 | `12920/UBND-NNMT` | TT Tỉnh ủy (báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 2045 | `12920/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2047 | `12920/UBND-NNMT` | Như trên | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2057 | `12919/UBND-NC` | Ban Pháp chế, HĐND tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2060 | `12919/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2074 | `12918/UBND-NNMT` | Trung đoàn 925 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2077 | `12918/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2092 | `12916/UBND-XDCT` | Đồng chí Được sự quan tâm lãnh đạo, chỉ đạo và hỗ trợ của Trung ương, tỉnh Gia Lai đã tổ chức triển khai dự án Đường cất hạ cánh số 2 và các công trình đồng | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2093 | `12916/UBND-XDCT` | bộ khu bay Cảng Hàng không Phù Cát | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2100 | `12915/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2101 | `12915/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 2108 | `12914/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2110 | `12913/UBND-NNMT` | N trê | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2115 | `12913/UBND-NNMT` | L u: VT, N1, N5 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2116 | `12912/UBND-XDCT` | Các cơ quan (có danh sách kèm theo) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2123 | `12912/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2134 | `12911/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2135 | `12911/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 2142 | `12910/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2149 | `12909/UBND-TD` | Ông Ung Văn Khôi (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2151 | `12909/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2154 | `12908/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2157 | `12908/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2166 | `12907/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2170 | `12906/UBND-KTTH` | Người đại diện phần vốn nhà nước tại Công ty cổ phần Đào tạo và Dịch vụ giao thông vận tải Bình Định | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2175 | `12906/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2183 | `12905/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2191 | `12904/UBND-KTTH` | Công ty TNHH Thịnh Phát – Muyuan | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2199 | `12904/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2209 | `12903/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2218 | `12902/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2228 | `12901/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2237 | `12900/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2248 | `12899/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2249 | `12899/UBND-TD` | HSVV-TD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, HSVV-TD'). |
| 2257 | `12898/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2266 | `12897/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2282 | `12896/UBND-NNMT` | Cty TNHH Kỹ thuật Nam Thiên Long | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2283 | `12896/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2290 | `12895/UBND-NNMT` | NgV | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, NgV'). |
| 2294 | `12895/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2302 | `12894/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2310 | `12893/UBND-XDCT` | Cảng Hàng không Phù Cát | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2315 | `12893/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2325 | `12892/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2334 | `12891/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2337 | `12890/UBND-KTTH` | Các cơ quan Trung ương trên địa bàn tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2338 | `12889/UBND-NC` | Đoàn Đại biểu Quốc hội tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2339 | `12889/UBND-NC` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 2342 | `12889/UBND-NC` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 2350 | `12889/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2356 | `12888/UBND-NNMT` | Các đơn vị quản lý, khai thác, vận hành hồ chứa thủy lợi, thủy điện trên địa bàn tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2361 | `12888/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2369 | `12887/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2380 | `12886/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2390 | `12885/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2398 | `12884/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2416 | `12883/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2419 | `12882/UBND-NNMT` | C H T Á L N . C H H V Ủ Ă T N Ị C PH H Ò NG | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2427 | `12882/UBND-NNMT` | TTPVHCC; Nguyễn Xuân Vĩnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2428 | `12882/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2429 | `12882/UBND-NNMT` | N , V 1 4, 9 | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N , V 1 4, 9'). |
| 2437 | `12881/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2438 | `12881/UBND-KGVX` | QTTV, VI | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2443 | `12880/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2448 | `12879/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2455 | `12878/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2461 | `12877/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2472 | `12876/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2477 | `12875/UBND-NNMT` | UBND các xã, phường: Cát Tiến, Phù Mỹ Đỹng, Phù Mỹ Bắc, An Hòa, Đề Gi, Quy Nhơn Đông, Ia Hia Hia Hai Hai Hai Hai Tai Tai Tai Tai Tai Tai Tai Tai Tai Hai Hai Hai Hai Tai Tai Tai Tai Rsai, Uar, Ia Ly, Đăk Song, Ia Dreh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2480 | `12875/UBND-NNMT` | Thường trực Tỉnh ủy (báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 2481 | `12875/UBND-NNMT` | Thường trực HĐND tỉnh (báo cáo) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2486 | `12875/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2489 | `12875/UBND-NNMT` | 12 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2500 | `12874/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2502 | `12874/UBND-XDCT` | X - CVP, PVPXD; 20 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2513 | `12873/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2517 | `12872/UBND-XDCT` | Ban Thường vụ Đảng ủy (b/c) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 2523 | `12872/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2535 | `12871/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2549 | `12869/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2554 | `12868/UBND-XDCT` | Công ty cổ phần Năng lượng Xanh ADG Bình Định | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2560 | `12868/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2571 | `12867/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2582 | `12866/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2595 | `12865/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2597 | `12865/UBND-NNMT` | Ngu | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, Ngu'). |
| 2607 | `12864/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2608 | `12864/UBND-KTTH` | T475 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2615 | `12863/UBND-PVHCC` | Trung tâm Hội nghị tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2616 | `12863/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2625 | `12862/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2636 | `12861/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2647 | `12860/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2659 | `12859/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2667 | `12858/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2678 | `12857/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2689 | `12856/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2700 | `12855/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2711 | `12854/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2722 | `12853/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2724 | `12852/UBND-KTTH` | Ông Kwon Hee Suk, Chủ tịch Công ty HanaTour Thưa Ông Chủ tịch, Tiếp nối những trao đổi trong chuyến công tác của Đoàn đại biểu tỉnh Gia Lai tại Hàn Quốc tháng 6/2026 và thư gửi Ông ngày 23/6/2026, tôi trân trọng kính mời Ông cùng Ban Lãnh đạo, các chuyên gia phát triển sản phẩm và đối tác của HanaTour đến thăm, khảo sát du lịch tại tỉnh Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2733 | `12851/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2738 | `12850/UBND-XDCT` | Các đơn vị cấp nước, thoát nước1 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2743 | `12850/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2754 | `12849/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2765 | `12848/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2772 | `12847/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2779 | `12846/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2784 | `12845/UBND-KTTH` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2788 | `12845/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2799 | `12844/UBND-NNMT` | Cty TNHH MTV Gốm Cổ | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2800 | `12844/UBND-NNMT` | Cty TNHH TH Long Vũ | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2801 | `12844/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2802 | `12844/UBND-NNMT` | N X 4, 1 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2803 | `12843/UBND-NC` | Thường trực Hội đồng nhân dân tỉnh Theo đề nghị của Thường trực HĐND tỉnh tại Công văn số 249/TTHĐND-VP ngày 05/10/2026 về việc đề nghị rà soát, đăng ký các nội dung trình tại các kỳ họp thường lệ năm 2027 của HĐND tỉnh khóa XIII, nhiệm kỳ 2026 - 2031 | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2808 | `12843/UBND-NC` | Các cơ quan TW đóng trên địa bàn tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2812 | `12843/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2820 | `12842/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2829 | `12841/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2832 | `12840/UBND-KTTH` | Công ty TNHH Đầu tư PNT Quy Nhơn | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2840 | `12840/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2849 | `12839/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2860 | `12838/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2861 | `12838/UBND-NNMT` | N , V 1 4, 9 | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N , V 1 4, 9'). |
| 2865 | `12837/UBND-XDCT` | Công ty TNHH MTV Petrolimex Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2871 | `12837/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2873 | `12836/UBND-KTTH` | Thường trực Hội đồng nhân dân tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2879 | `12836/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2881 | `12835/UBND-KTTH` | Các cơ quan, đơn vị, địa phương (theo phụ lục đính kèm) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2885 | `12835/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2890 | `12834/UBND-NC` | Công ty TNHH Tân Lập | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2895 | `12834/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2902 | `12833/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2912 | `12832/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2921 | `12831/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2930 | `12830/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2938 | `12829/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2945 | `12828/UBND-KGVX` | Hiệp hội doanh nghiệp tỉnh, | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 2948 | `12828/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2959 | `12827/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2972 | `12826/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2980 | `12825/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2988 | `12824/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 2992 | `12823/UBND-NNMT` | Công ty TNHH Thương mại Vinh Quang 1 | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 2999 | `12823/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3004 | `12822/UBND-KTTH` | Căn cứ Quyết định số 3009/QĐ-UBND ngày 12/12/2025 của UBND tỉnh Gia Lai về việc phân bố và giao kế hoạch đầu tư công vôn ngân sách nhà nước năm | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3005 | `12822/UBND-KTTH` | 2026 và các Quyết định điều chỉnh, bố sung có liên quan; xét đề nghị của Sở Tài chính tại Văn bản số 10727/STC-QLNS ngày 16/10/2026 về việc giải ngân các dự án, công trình từ nguồn thu tiền sử dụng đất và xổ số kiến thiết năm 2026, Chủ tịch UBND tỉnh có ý kiến như sau: 1. Cho phép sử dụng số tiền 1.534.811 triệu đồng từ các nguồn vốn theo đề | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3006 | `12822/UBND-KTTH` | xuất của Sở Tài chính tại Văn bản số 10727/STC-QLNS nêu trên, đề thông báo giải | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3007 | `12822/UBND-KTTH` | ngân cho các dự án, công trình đã bố trí kế hoạch vốn từ nguồn thu tiền sử dụng đất | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3008 | `12822/UBND-KTTH` | ngân sách tỉnh năm 2026 (chi tiết theo phụ lục đính kèm) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3009 | `12822/UBND-KTTH` | 2. Sở Tài chính chủ trì, phối hợp với các cơ quan, đơn vị có liên quan tham mưu, đề xuất việc điều hành ngân sách nhà nước đảm bảo cân đối thu chi, có nguyên tắc, tiêu chí ưu tiên thanh toán cho các dự án, công trình từ nguồn thu tiền sử dụng đất và xổ số kiến thiết năm 2026 đảm bảo theo quy định pháp luật và phù hợp tình hình thực tế địa phương Thủ trưởng các cơ quan, đơn vị có liên quan phối hợp triển khai thực hiện./. MM | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3014 | `12822/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3016 | `12822/UBND-KTTH` | Inn | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3022 | `12821/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3032 | `12820/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3041 | `12819/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3050 | `12818/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3059 | `12817/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3064 | `12816/UBND-NNMT` | Hiệp hội Thủy sản tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3069 | `12816/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3078 | `12815/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3090 | `12814/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3098 | `12813/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3104 | `12812/UBND-XDCT` | Công ty TNHH MTV Nhiên liệu Hàng không Việt Nam | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3109 | `12812/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3119 | `12811/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3127 | `12810/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3130 | `12809/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3133 | `12809/UBND-NC` | CQ CSĐT Công an tỉnh Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3135 | `12809/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3146 | `12808/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3160 | `12807/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3165 | `12806/UBND-NNMT` | VP Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3168 | `12806/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3179 | `12805/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3182 | `12804/UBND-XDCT` | Công ty cổ phần Tập đoàn Đầu tư Hoàng Gia Việt Nam | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3192 | `12804/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3194 | `12803/UBND-XDCT` | Tổng công ty Điện lực miền Trung (EVNCPC) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3196 | `12803/UBND-XDCT` | Công ty cổ phần Điện gió Chư Pơng | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3202 | `12803/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3211 | `12802/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3218 | `12801/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3232 | `12800/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3234 | `12799/UBND-XDCT` | Trung tâm Hành động Bom mìn Quốc gia Việt Nam Theo đề nghị của Trung tâm Hành động Bom mìn Quốc gia Việt Nam tại Văn bản số 1316/VNMAC-KHĐP ngày 11/10/2026 về kiện toàn Ban Điều phối dự án “Hành động bom mìn vì làng hòa bình Việt Nam - Hàn Quốc” | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3240 | `12799/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3246 | `12798/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3247 | `12798/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3249 | `12798/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3257 | `12797/UBND-XDCT` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 3261 | `12797/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3272 | `12796/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3284 | `12795/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3295 | `12794/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3301 | `12793/UBND-KGVX` | Bệnh viện đa khoa tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3302 | `12793/UBND-KGVX` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3310 | `12793/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3318 | `12792/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3326 | `12791/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3335 | `12790/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3339 | `12789/UBND-XDCT` | Ban quản lý dự án Recaf Gia Lai | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3346 | `12789/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3356 | `12788/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3364 | `12787/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3371 | `12786/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3382 | `12785/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3393 | `12784/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3404 | `12783/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3412 | `12782/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3421 | `12781/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3430 | `12780/UBND-KTTH` | T M | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, T M'). |
| 3435 | `12780/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3437 | `12780/UBND-KTTH` | P. QT-TV | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3438 | `12779/UBND-NC` | Cơ quan chuyên môn thuộc Ủy ban nhân dân tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3445 | `12779/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3455 | `12778/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3464 | `12777/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3475 | `12776/UBND-TD` | Ông Thái Hùng Vĩ (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3476 | `12776/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3486 | `12775/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3493 | `12774/UBND-KTTH` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 3500 | `12774/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3506 | `12773/UBND-KTTH` | Người đại diện phần vốn nhà nước tại 02 CTCP: Khoáng sản Bình Định | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3512 | `12773/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3520 | `12772/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3532 | `12771/UBND-TD` | Bà Đặng Thị Yến (để biết); N | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3533 | `12771/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3544 | `12770/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3553 | `12769/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3555 | `12769/UBND-KTTH` | P.QT-TV | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3565 | `12768/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3574 | `12766/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3582 | `12765/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3587 | `12764/UBND-NNMT` | Công ty TNHH MTV Cao su Chư Prông | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3592 | `12764/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3600 | `12763/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3605 | `12762/UBND-KGVX` | HHVHAT tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3608 | `12762/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3617 | `12761/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3627 | `12760/UBND-KGVX` | Các sở, ban, ngành liên quan | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3629 | `12760/UBND-KGVX` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3635 | `12760/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3645 | `12759/UBND-KGVX` | Các doanh nghiệp viễn thông trên địa bàn tỉnh (VNPT, Viettel, MobiFone) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3649 | `12759/UBND-KGVX` | Đài Thông tin duyên hải Quy Nhơn | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3652 | `12759/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3664 | `12758/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3675 | `12757/UBND-PVHCC` | Các cơ quan chuyên môn thuộc tỉnh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3677 | `12757/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3684 | `12756/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3686 | `12756/UBND-XDCT` | Như trên | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3693 | `12755/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3705 | `12754/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3713 | `12753/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3722 | `12752/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3723 | `12752/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 3731 | `12751/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3739 | `12750/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3741 | `12749/UBND-TD` | Ông Cao Văn Gương Địa chỉ: Tổ 4, khu phố 6, phường Quy Nhơn Tây, tỉnh Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3750 | `12749/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3751 | `12749/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 3761 | `12748/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3767 | `12747/UBND-XDCT` | Hợp tác xã Nông nghiệp Ân Tín | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3771 | `12747/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3780 | `12746/UBND-XDCT` | Công ty TNHH Thiên Hưng Mỹ Thọ | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3785 | `12746/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3796 | `12745/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3798 | `12744/UBND-XDCT` | Tổng công ty Điện lực miền Trung Trong thời gian tới, Trạm Y tế xã Canh Liên, tỉnh Gia Lai được đầu tư nâng cấp, mở rộng và trang bị bổ sung các thiết bị y tế phục vụ công tác khám, chữa bệnh (trong đó có thiết bị X-quang và một số thiết bị yêu cầu sử dụng nguồn điện 3 pha) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3806 | `12744/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3816 | `12743/UBND-KGVX` | Hiệp hội doanh nghiệp tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3820 | `12743/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3827 | `12742/UBND-KTTH` | Trên cơ sở báo cáo của Sở Tài chính và để tăng cáờ chỉ đạo, kip thời tháo gõ khó khăn, vướng mắc, tiên độ giải ngân thực hiện các dự án vốn đầu tư | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3828 | `12742/UBND-KTTH` | công và Chương trình mục tiêu quốc gia các tháng cao điểm cuối năm 2026; góp | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3829 | `12742/UBND-KTTH` | phần nâng cao hiệu quả sử dụng vốn đầu tư, chống thất thoát, lãng phí nguôn lực | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3830 | `12742/UBND-KTTH` | đầu tư, tạo động lực thúc đầy phát triển kinh tế - xã hội, phấn đầu hoàn thành mục | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3831 | `12742/UBND-KTTH` | tiêu tăng trưởng hai con số năm 2026; theo phân công nhiệm vụ Chủ tịch, các Phó Chủ tịch UBND tỉnh nhiệm kỳ 2026 ? 2031 tại Quyết định số 2800/QĐ-UBND ngày 30/6/2026, Chủ tịch có ý kiến như sau: 1. Các đồng chí Phó Chủ tịch UBND tỉnh theo chức năng, nhiệm vụ, lĩnh vực được phân công phụ trách, trực tiếp theo dõi, chỉ đạo, đôn đốc các chủ đầu tư, sở, ban, ngành, UBND các xã, phường và các cơ quan, đơn vị có liên quan tăng cường công tác giải | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3832 | `12742/UBND-KTTH` | ngân và triên khai thực hiện các dự án theo Phụ lục phân công (kèm theo Phụ lục 1), Kịp thời chỉ đạo tháo gỡ khó khăn, vướng mắc hoặc báo cáo, đề xuất Chủ tịch UBND tỉnh xem xét, chỉ đạo đối với những nội dung vượt thấm quyền, chịu trách nhiệm trước Chủ tịch UBND tỉnh nếu dự án được phân công theo dõi, đôn đốc chậm tiến độ giải ngân do vướng thủ tục, không bảo đảm giải ngân kế hoạch vôn đã được thông báo theo quy định 2. Định kỳ hằng tuần, các đồng chí Phó Chủ tịch chủ động nắm tình hình, báo cáo kết quả thực hiện tại hội ý lãnh đạo UBND tỉnh (nội dung báo cáo nêu rõ | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3833 | `12742/UBND-KTTH` | phân loại các nhóm vướng mắc, dự án chậm tiến độ, nguyên nhân và đề xuất hướng xử lý) 3. Giao Sở Tài chính phân công lãnh đạo Sở và đầu mối theo dõi đối với các dự án, chủ trì, phối hợp các Chủ đầu tư phân loại các nhóm khó khăn, vướng mắc và đề xuất giải pháp để báo cáo Lãnh đạo UBND tỉnh xem xét, chỉ đạo đảm bảo theo quy định | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3834 | `12742/UBND-KTTH` | Đề nghị các đồng chí Phó Chủ tịch UBND tỉnh khẩn trương triển khai thực hiện// la | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3837 | `12742/UBND-KTTH` | Các sở, ban, ngành, Chủ đầu tư | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3839 | `12742/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3845 | `12741/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3846 | `12741/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3848 | `12741/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3856 | `12740/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3862 | `12739/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3865 | `12738/UBND-XDCT` | Công ty TNHH Shine Green Energy Việt Nam | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3874 | `12738/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3883 | `12737/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3894 | `12736/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3904 | `12735/UBND-TD` | Ông Nguyễn Đức Quy (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3905 | `12735/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3908 | `12734/UBND-KGVX` | Hội Người cao tuổi tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3910 | `12734/UBND-KGVX` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 3916 | `12734/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3919 | `12733/UBND-KGVX` | Hội Bảo trợ bệnh nhân nghèo | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3929 | `12733/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3940 | `12732/UBND-TD` | Ông Dương Hào (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3942 | `12732/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3943 | `12732/UBND-TD` | HSVV-TD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, HSVV-TD'). |
| 3952 | `12731/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3955 | `12730/UBND-KGVX` | Cảng hàng không Phù Cát | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3956 | `12730/UBND-KGVX` | Công ty Cổ phần Tập đoàn FLC | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3957 | `12730/UBND-KGVX` | Hãng hàng không Bamboo Airways | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 3960 | `12730/UBND-KGVX` | Thường trực Tỉnh ủy (để b/c) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 3965 | `12730/UBND-KGVX` | Hiệp hội Du lịch tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 3967 | `12730/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3974 | `12730/UBND-KGVX` | Ng | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, Ng'). |
| 3982 | `12729/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 3993 | `12728/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4003 | `12727/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4005 | `12726/UBND-KGVX` | Các sở, ban ngành và đơn vị thuộc tỉnh Ngày 14/10/2026, UBND tỉnh nhận được Văn bản số C60616/YC-CSKT ngày 05/10/2026 của Cơ quan Cảnh sát điều tra Công an Thành phố Hồ Chí Minh về việc yêu cầu cung cấp chứng cứ, đồ vật, tài liệu, dữ liệu điện tử liên quan đến Công ty Cổ phần Redeyes và bà Thái Thị Thu Đào (sao gửi văn bản đến các đơn vị). Để bảo đảm cung cấp đầy đủ, chính xác thông tin, tài liệu theo yêu cầu của Cơ quan điều tra, Chủ tịch UBND tỉnh có ý kiến như sau: 1. Giao các sở, ban, ngành, đơn vị thuộc tỉnh và các cơ quan có liên quan theo chức năng, nhiệm vụ và phạm vi quản lý, khẩn trương tổ chức kiểm tra, rà soát, thu thập, cung cấp đầy đủ hồ sơ, tài liệu, văn bản, chứng cứ và dữ liệu điện tử liên quan đến Công ty Cổ phần Redeyes, bà Thái Thị Thu Đào và việc đề xuất triển khai “Chương trình phát triển kinh tế - văn hóa - giáo dục - y tế khu vực Tây Nguyên và miền Trung” từ năm 2023 đến nay; trong đó tập trung: a) Về hồ sơ, tài liệu tiếp nhận và quá trình xử lý: Rà soát toàn bộ văn bản, đơn đề nghị, tờ trình, đề án, chương trình, kế hoạch và các tài liệu do Công ty Cổ phần Redeyes hoặc bà Thái Thị Thu Đào gửi đến UBND tỉnh, Văn phòng UBND tỉnh và các sở, ban, ngành trực thuộc; cung cấp hồ sơ tiếp nhận, văn bản chuyển xử lý, giao nhiệm vụ, tài liệu thẩm định, ý kiến tham gia của các cơ quan, đơn vị, phiếu trình, báo cáo tham mưu, văn bản chỉ đạo, kết quả giải quyết và văn bản phản hồi, trả lời (nếu có). Làm rõ thời gian, hình thức, đơn vị tiếp nhận và quá trình xử lý đối với từng hồ sơ, văn bản | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4006 | `12726/UBND-KGVX` | Như trên (thực hiện) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4007 | `12726/UBND-KGVX` | Cơ quan Cảnh sát điều tra Công an Thành phố Hồ Chí Minh | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4012 | `12726/UBND-KGVX` | Phòng KGVX – VP UBND tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4013 | `12726/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4027 | `12725/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4034 | `12724/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4038 | `12723/UBND-XDCT` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4048 | `12723/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4055 | `12722/UBND-XDCT` | Các chủ đầu tư | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4061 | `12722/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4074 | `12721/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4089 | `12719/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4096 | `12718/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4104 | `12717/UBND-KTTH` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 4108 | `12717/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4118 | `12716/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4122 | `12715/UBND-NC` | Công ty TNHH Xổ số kiến thiết Bình Định | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4125 | `12715/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4126 | `12715/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4128 | `12715/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4139 | `12714/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4145 | `12713/UBND-KGVX` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 4150 | `12713/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4162 | `12712/UBND-TD` | Ông Mai Xuân Nam (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4163 | `12712/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4164 | `12712/UBND-TD` | HSVV, Vinh. N | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4172 | `12711/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4175 | `12710/UBND-KGVX` | Ban đại diện Hội Người cao tuổi tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4177 | `12710/UBND-KGVX` | Thường trực Tỉnh ủy (báo cáo) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4178 | `12710/UBND-KGVX` | Thường trực HĐND tỉnh (báo cáo) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4185 | `12710/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4196 | `12709/UBND-PVHCC` | VNPT Gia Lai | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4197 | `12709/UBND-PVHCC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4201 | `12708/UBND-XDCT` | Công ty CP XD & QLSC Cầu đường Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4206 | `12708/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4221 | `12707/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4223 | `12707/UBND-XDCT` | Ng | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, Ng'). |
| 4237 | `12706/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4244 | `12705/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4251 | `12704/UBND-NNMT` | NV | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4256 | `12704/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4264 | `12703/UBND-XDCT` | Các nhà đầu tư (giao UBND xã Chư Sê sao gửi) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4267 | `12703/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4271 | `12702/UBND-NNMT` | Công ty Cổ phần Hòa Việt | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4276 | `12702/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4286 | `12701/UBND-TD` | Ông Nguyễn Văn Thanh (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4288 | `12701/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4299 | `12699/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4307 | `12698/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4309 | `12697/UBND-XDCT` | Chủ đầu tư các dự án điện trên địa bàn tỉnh1 Thời gian qua, UBND tỉnh, các đồng chí Lãnh đạo UBND tỉnh đã thường xuyên có nhiều văn bản chỉ đạo và trực tiếp kiểm tra tại hiện trường, làm việc với các sở, ngành, địa phương, nhà đầu tư dự án để tháo gỡ khó khăn, vướng mắc, đôn đốc đẩy nhanh tiến độ | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4320 | `12697/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4330 | `12696/UBND-TD` | Các công dân nêu trên (để biết) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4332 | `12696/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4338 | `12695/UBND-KTTH` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 4342 | `12695/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4353 | `12694/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4360 | `12693/UBND-XDCT` | Công ty cổ phần Thị Nại Eco Bay | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4365 | `12693/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4374 | `12692/UBND-XDCT` | Công ty TNHH Môi trường Phú Hà | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4379 | `12692/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4391 | `12691/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4394 | `12690/UBND-KGVX` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 4400 | `12690/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4409 | `12689/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4410 | `12689/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4412 | `12689/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4418 | `12688/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4419 | `12688/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4421 | `12688/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4424 | `12687/UBND-NC` | Công ty cổ phần Đào tạo và Dịch vụ | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4427 | `12687/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4428 | `12687/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4430 | `12687/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4436 | `12686/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4437 | `12686/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4439 | `12686/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4445 | `12685/UBND-NC` | Thường trực Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4446 | `12685/UBND-NC` | Ban Tổ chức Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4448 | `12685/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4451 | `12684/UBND-KTTH` | (đồng thời gửi Cục Thuế - Bộ Tài chính), Chủ tịch có ý kiến cụ thể sau: | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4454 | `12684/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4455 | `12684/UBND-KTTH` | TS - CVP, PVPTH | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4456 | `12683/UBND-NNMT` | Chủ tịch UBND phường Quy Nhơn | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4463 | `12683/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4465 | `12682/UBND-KGVX` | Ban Thường vụ Đảng ủy UBND tỉnh | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4466 | `12682/UBND-KGVX` | TM | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TM'). |
| 4471 | `12682/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4483 | `12681/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4485 | `12680A/UBND-KTTH` | Ngài Peter Styles, Thị trưởng thành phố Darwin, Vùng Lãnh thổ Bắc Australia AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4487 | `12680/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4494 | `12680/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4496 | `12679/UBND-KTTH` | Giáo sư Fiona Coulson, Hiệu trưởng kiêm Chủ tịch Đại học Charles Darwin, AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4500 | `12678/UBND-KGVX` | 2. Giao Sở Tài chính chủ trì, phối hợp với Sở Văn hóa, Thế thao và Du lịch tham mưu bố trí đảm bảo kinh phí thực hiện để trình cấp có thấm quyền xem xét | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4501 | `12678/UBND-KGVX` | Thường trực Tỉnh ủy (để b/c) | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4507 | `12678/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4512 | `12677/UBND-KTTH` | Ông Peter Dummett, Tổng Giám đốc Cảng Darwin, Vùng Lãnh thổ Bắc Australia, AUSTRALIA | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4513 | `12676/UBND-KTTH` | Giáo sư, Tiến sĩ Nghiêm Đức Long, Chủ tịch Hội Trí thức và Chuyên gia Việt Nam - Australia (VASEA) AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4514 | `12675/UBND-KTTH` | Ông Trần Bá Phúc, Chủ tịch Hội Doanh nhân Việt Nam tại Australia (VBAA) AUSTRALIA | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4515 | `12674/UBND-KTTH` | Ban lãnh đạo Công ty SW Accountants & Advisors AUSTRALIA | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4516 | `12673/UBND-KTTH` | Ban lãnh đạo Tribeca Investment Partners AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4517 | `12672/UBND-KTTH` | Bà Charishma Kaliyanda, Nghị sĩ Hạ viện bang New South Wales, đại diện khu vực bầu cử Liverpool AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4518 | `12671/UBND-KTTH` | Tiến sĩ Frank Alafaci, Chủ tịch Hội đồng Thượng đỉnh Doanh nghiệp Australia (ABSC) AUSTRALIA | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4519 | `12670/UBND-KTTH` | Ông Kim Sampson, Chủ tịch Hội Hữu nghị Australia - Việt Nam (AVFS) AUSTRALIA | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4520 | `12669/UBND-KTTH` | Ông Paul Bradley, Giám đốc điều hành Allambie Heights Village Ltd | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4521 | `12668/UBND-KTTH` | Ông Ben Lever, Đại diện Beanstalk AgTech tại Sydney AUSTRALIA | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4532 | `12667/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4544 | `12666/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4546 | `12665/UBND-KTTH` | Đồng chí Phạm Hùng Tâm, Đại sứ đặc mệnh toàn quyền nước Cộng hòa xã hội chủ nghĩa Việt Nam tại Australia | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4554 | `12665/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4564 | `12664/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4566 | `12663/UBND-KTTH` | Tổng Lãnh sự quán Việt Nam tại Perth, Australia | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4574 | `12663/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4582 | `12662/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4587 | `12661/UBND-XDCT` | Chủ đầu tư hạ tầng các Khu công nghiệp | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4592 | `12661/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4601 | `12660/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4605 | `12659/UBND-NC` | Thường trực Tỉnh ủy | `PARTY_COMMITTEE_CHANNEL` | Cơ quan/thường trực Đảng ủy/Tỉnh ủy gửi qua kênh bảo mật của Đảng hoặc bản giấy, không có mã e-document. |
| 4612 | `12659/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4620 | `12658/UBND-KTTH` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 4623 | `12658/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4632 | `12657/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4644 | `12656/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4653 | `12655/UBND-KTTH` | TP | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, TP'). |
| 4656 | `12655/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4665 | `12654/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4669 | `12653/UBND-TD` | địa chỉ: Thôn Thăng Hưng Đông | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4670 | `12653/UBND-TD` | xã Bàu Cạn | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4671 | `12653/UBND-TD` | tỉnh Gia Lai; nội dung: Khiếu nại Quyết định số 1286/QĐ-UBND ngày 27/8/2013 của UBND thành Pleiku (cũ) về việc thu hồi Giấy chứng nhận quyền sử dụng đất đối với thửa đất tại thôn Hàm Rồng | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4672 | `12653/UBND-TD` | xã Chư Hdrông (nay là phường Hội Phú). Về việc này | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4673 | `12653/UBND-TD` | Chủ tịch UBND tỉnh có ý kiến như sau: | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4678 | `12653/UBND-TD` | Bà Phạm Thị Kim Yến | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4679 | `12653/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4680 | `12653/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 4681 | `12652/UBND-KTTH` | Ủy ban nhân dân tỉnh Gia Lai trân trọng cảm ơn sự quan tâm, giúp đỡ và hỗ trợ quý báu của Quý cơ quan đối với tỉnh Gia Lai trong những năm qua | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4682 | `12652/UBND-KTTH` | Nhằm tăng cường hơn nữa quan hệ hợp tác hữu nghị, thúc đầy giao lưu kinh tế và giới thiệu tiêm năng, môi trường đầu tư của tỉnh Gia Lai đến cộng đồng doanh nghiệp và các đôi tác Nhật Bản, Ủy ban nhân dân tỉnh Gia Lai sẽ tổ chức Hội nghị xúc tiến đầu tư, thương mại và du lịch tỉnh Gia Lai tại Nhật Bản năm 2026? tại Tokyo, Nhật Bản. Thô như sau: | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4683 | `12652/UBND-KTTH` | Thời gian: 09 giờ 30, ngày 21 tháng 10 năm 2026 (Sáng thứ Tư) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4684 | `12652/UBND-KTTH` | Địa điểm: Khách sạn Shibuya Excel Hotel Tokyu, số 1-12-2 Dogenzaka, Shibuya-ku, Tokyo 150-0043, Nhật Bản | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4688 | `12652/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4695 | `12651/UBND-KTTH` | Công ty cổ phần Nafoods Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4700 | `12651/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4713 | `12650/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4723 | `12649/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4727 | `12648/UBND-XDCT` | Chủ đầu tư dự án1 | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4734 | `12648/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4739 | `12647/UBND-XDCT` | Công ty cổ phần Điện gió Quang Đức | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4744 | `12647/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4755 | `12646/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4763 | `12645/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4764 | `12645/UBND-NNMT` | N , , X | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, N , , X'). |
| 4766 | `12644/UBND-NNMT` | Quỹ Phòng, chống thiên tai tỉnh | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4771 | `12644/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4780 | `12643/UBND-KGVX` | Công ty Cổ phần Y dược Hồng Phúc | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4781 | `12643/UBND-KGVX` | Liên danh Công ty Cổ phần Barin và Công ty TNHH Tổ hợp Y tế Phương Đông | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4787 | `12643/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4796 | `12642/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4800 | `12641/UBND-NC` | Như trên; CH | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4803 | `12641/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4806 | `12640/UBND-TD` | Ông Rơ Châm Lơi, địa chỉ: Làng Dăng, xã Ia O, tỉnh Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4815 | `12640/UBND-TD` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4816 | `12640/UBND-TD` | BTCD | `INTERNAL_FILING_OR_SPECIALIST_CODE` | Ký hiệu chuyên viên/phòng ban hoặc hồ sơ vụ việc trong mục Lưu ('Lưu: VT, BTCD'). |
| 4826 | `12639/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4851 | `12638/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4859 | `12637/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4867 | `12636/UBND-XDCT` | Công ty cổ phần thủy điện Hoa Tuyết Hoa Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4872 | `12636/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4880 | `12635/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4892 | `12634/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4899 | `12633/UBND-KGVX` | Phân hiệu Trường Đại học Lâm nghiệp tại Gia Lai | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 4904 | `12633/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4906 | `12632/UBND-KTTH` | Công ty Cổ phần Phú Tài | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4914 | `12632/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4924 | `12631/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4927 | `12630/UBND-KTTH` | Công ty Cổ phần May Tam Quan | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4944 | `12629/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4958 | `12628/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4966 | `12627/UBND-KTTH` | Công ty TNHH Tây Bắc Gia Lai | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4971 | `12627/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4976 | `12626/UBND-NNMT` | Công ty TNHH Thịnh Hưng Nguyên | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 4981 | `12626/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4990 | `12625/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 4998 | `12624/UBND-KGVX` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5006 | `12623/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5017 | `12622/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5024 | `12621/UBND-KTTH` | Công ty cổ phần Công nghệ tài nguyên năng lượng Tây Nguyên | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5029 | `12621/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5032 | `12620/UBND-NNMT` | Ban Quản lý dự án các công trình | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5037 | `12620/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5041 | `12619/UBND-NC` | Bộ Dân tộc và Tôn giáo (Vụ Pháp chế) | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 5047 | `12619/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5053 | `12618/UBND-XDCT` | Công ty TNHH Happy House GL | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5057 | `12618/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5065 | `12617/UBND-XDCT` | Công ty cổ phần Thủy điện Ia O | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5070 | `12617/UBND-XDCT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5073 | `12616/UBND-KTTH` | Các cơ quan, đơn vị (theo phụ lục đính kèm) | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5077 | `12616/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5088 | `12615/UBND-KTTH` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5093 | `12614/UBND-NNMT` | Quân đoàn 34 | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 5094 | `12614/UBND-NNMT` | Lữ đoàn Thông tin 132 | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5095 | `12614/UBND-NNMT` | Trường Trung cấp 24 Biên phòng | `UNMAPPED_EXTERNAL_OR_SPECIFIC` | Cơ quan ngoài tỉnh/đơn vị đặc thù chưa có mã định danh trong danh mục đơn vị nhận. |
| 5096 | `12614/UBND-NNMT` | Cảng Hàng không Pleiku | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5101 | `12614/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5110 | `12613/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5116 | `12612/UBND-NNMT` | Công ty TNHH MTV Cà phê Ia Blan | `COMPOSITE_OR_INDIVIDUAL` | Nhóm đối tượng tổng hợp, cá nhân công dân hoặc nơi nhận 'Như trên', không ánh xạ 1-1 đơn vị nhận. |
| 5119 | `12612/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5129 | `12611/UBND-NC` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
| 5137 | `12610/UBND-NNMT` | VT | `POLICY_ARCHIVAL_VT` | Ký hiệu lưu trữ văn thư ('Lưu: VT'). Không phải đơn vị nhận văn bản. |
