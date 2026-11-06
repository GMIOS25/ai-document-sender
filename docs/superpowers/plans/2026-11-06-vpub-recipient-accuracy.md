# Kế hoạch nâng độ chính xác nơi nhận VPUB lên 95–99%

Ngày 06/11/2026. Phạm vi gồm backend nhận diện nơi nhận và phần userscript cần thiết để điền đúng nhóm trên iDesk.

**Mục tiêu.** Đạt ít nhất **95% văn bản khớp toàn bộ tập đích** trên bộ kiểm tra mới đã khóa. Mốc **99%** áp dụng cùng cách đo. Chấm kết quả backend trước khi văn thư chỉnh sửa, sau khi quy đổi node cha và nhóm thành đúng các ID nhận thực tế.

**Thiết kế hiện hành.** Giữ luồng đọc PDF → trích xuất kèm bằng chứng → resolve theo danh bạ và quy tắc đã xác nhận → lập phương án điền iDesk. Tận dụng Python, SQLite, snapshot danh bạ, checkpoint extraction và userscript hiện có. Kế hoạch dựa trên [đặc tả backend](../specs/2026-10-07-outgoing-backend-design.md) và [quy trình đánh giá](../../evaluation.md).

## Mốc xuất phát và tiêu chí nghiệm thu

Test 1 trên 500 văn bản có 48 văn bản khớp toàn bộ (9,60%), bao phủ 4.517/16.031 lượt đích (28,18%) và khớp 4.517/4.575 lượt đã chọn (98,73%). Đây là mốc đối chiếu theo tên với danh bạ của lượt chạy đó. Chấm theo ID cần dựng lại mốc trên cùng bộ dữ liệu đã xác minh. [Báo cáo đối soát](../../../var/target-comparison-2026-11-05/bao-cao-doi-soat.md)

| Phép đo | Điều kiện và cách đọc |
| --- | --- |
| Exact set match | Tập ID dự đoán bằng tập ID đích của văn bản sau khi mở rộng node/nhóm và loại trùng. Thiếu hoặc thừa một đích thì văn bản chưa khớp. |
| Mốc nghiệm thu 95% | Nếu bộ kiểm tra có 500 văn bản đã xác minh, ít nhất 475 văn bản khớp toàn bộ. |
| Mốc cao hơn 99% | Trên cùng quy mô và cách chấm, ít nhất 495/500 văn bản khớp toàn bộ. Hai ngưỡng là điểm đo trên mẫu. Báo thêm khoảng tin cậy Wilson 95% để thể hiện độ bất định. |
| Chỉ số chẩn đoán | Precision và recall theo ID, tách người nội bộ và đơn vị. Báo recall trung bình theo văn bản, lỗi provider, tỷ lệ cần rà soát và số ca chưa đủ nhãn. |
| Kiểm chứng điền iDesk | So tập ID/mã và phạm vi trong/ngoài tỉnh ở các trường đã điền. Kiểm tra cả phần tử thiếu lẫn phần tử ngoài phạm vi. Điểm này báo riêng với điểm nhận diện backend. |

Chấm mọi văn bản có đáp án xác minh được, kể cả job lỗi, thiếu kết quả, partial hoặc cần rà soát. Các ca chưa có đủ dữ liệu để xác nhận đáp án được ghi trong báo cáo riêng với số lượng, lý do và cách thu thập lại. Chốt phạm vi và danh sách ca cần xác minh trước khi xem kết quả thử. Bộ 500 đã dùng để học luật là bộ phát triển và hồi quy. Bộ nghiệm thu dự kiến gồm **500 văn bản mới**, lấy theo quy trình lấy mẫu đã định trước, tách theo thời gian, hash PDF và mẫu văn bản. Giữ một bộ validation để chỉnh luật và một bộ ca khó riêng để thử tình huống gửi nhầm.

## 1. Khóa dữ liệu đánh giá và lập mốc theo ID

**Phụ thuộc.** Bắt đầu ngay. Cơ sở cho các bước so sánh sau.

- [ ] Ghép số hiệu, ID văn bản và hash PDF. Đối chiếu hai nguồn độc lập gồm bằng chứng từ PDF và lịch sử gửi iDesk. Lưu định danh người, mã đơn vị, sphere, ID nhóm gốc nếu có, snapshot thành viên và thời điểm quan sát.
- [ ] Khôi phục danh sách thực nhận đầy đủ cho 53 bản ghi có `book.receiver` kết thúc bằng dấu ba chấm và kiểm tra thêm bản ghi 12778/UBND-NNMT có cùng độ dài 4.094 ký tự. Trong 62 ca có cụm chung về xã/phường, cả 51 ca mà thẻ đích liệt kê dưới 135 xã/phường đều có dấu hiệu cắt rõ ràng ở nguồn. Đối chiếu lịch sử gửi đầy đủ, phạm vi PDF và thành viên có hiệu lực trước khi xác nhận số đích.
- [ ] Tạo manifest cố định cho bộ hồi quy, validation và holdout. Duyệt nhãn trước khi xem dự đoán. Lưu riêng trường hợp chỉ có tên, chưa chắc identity hoặc không tìm được bằng chứng nguồn.
- [ ] Mở rộng `tools/evaluate_outgoing.py` để đối chiếu tập ID sau khi quy đổi bằng cùng một snapshot. Thử node cha bằng đúng các con, nhóm lệch một thành viên, người nhận trùng và kết quả thiếu/khác version. Khi đã xác minh gold nhưng không thể kiểm chứng membership của dự đoán, đánh dấu ca chưa khớp và báo lý do.
- [ ] Chạy mốc Test 1 trên phần dữ liệu đã xác minh. Xuất từng ca gồm thiếu, thừa, lý do và số ca chấm được. Giữ số 9,60% làm mốc lịch sử theo tên.

**Kiểm chứng.** `python -m pytest tests/test_evaluation.py -q`. Chạy `python tools/evaluate_outgoing.py --gold <gold.json> --predictions <predictions.jsonl> --output <score.json>`. Đối chiếu lại mẫu số, version, hash và hai ca kiểm tra thủ công có nhóm.

## 2. Ổn định đường trích xuất qua provider

**Phụ thuộc.** Có thể chẩn đoán song song với bước 1. Cần qua bước này trước khi chạy lô lớn có model.

- [ ] Tái hiện lỗi bằng dữ liệu giả lập. Test 1 có 478/500 văn bản lỗi HTTP ở khâu trích xuất. Báo cáo thử nghiệm ngày 05/11 tái hiện 404 khi bắt buộc `response_format` với endpoint text đã cấu hình và ghi nhận phản hồi vision bọc trong khối Markdown. Mã nhánh hiện tại vẫn có `openrouter-v2`. [Báo cáo chẩn đoán](../../../var/recipient-coverage/provider-report.md)
- [ ] Trong `provider.py`, chọn dạng yêu cầu theo khả năng endpoint được xác minh. Luôn kiểm tra JSON, schema và bằng chứng ở backend. Giới hạn sửa lại JSON và retry. Dừng lô lớn khi lỗi cấu hình lặp lại, giữ timeout và rate limit ở nhóm lỗi riêng.
- [ ] Ghi model, phiên bản prompt, phiên bản extraction, mã lỗi đã làm sạch và thời gian. Thay phiên bản xử lý khi thay cách gọi model để lượt chạy sau dùng checkpoint tương thích.
- [ ] Chạy preflight text/vision bằng dữ liệu giả lập. Sau đó chạy thử **5–10 PDF đại diện** bằng môi trường xử lý đã được xác nhận, gồm PDF text, scan, hybrid và tham chiếu. Đọc từng lỗi trước khi tăng số lượng.

**Kiểm chứng.** `python -m pytest tests/test_provider.py tests/test_extraction.py tests/test_jobs.py -q`. Preflight text/vision trả JSON hợp lệ. Lượt nhỏ qua các đường xử lý dự kiến với 0 lỗi HTTP 400/404 do cấu hình. Đối chiếu thủ công text và bằng chứng của từng PDF trong lượt nhỏ trước khi mở rộng.

## 3. Đo phần cải thiện từ danh bạ hiện hành

**Phụ thuộc.** Có manifest và phép đo bước 1. Có thể dùng checkpoint tương thích để cô lập tác động của danh bạ.

- [ ] Dùng đồng bộ hiện có cho tenant VPUB, theo mã + sphere. Kiểm tra Sở Ngoại vụ, Thanh tra tỉnh và các đơn vị thiếu nhiều trong Test 1. Giữ nguồn, thời điểm và độ đầy đủ của mỗi lần đồng bộ.
- [ ] Resolve lại trên cùng extraction với snapshot danh bạ cũ và mới. Chỉ dùng checkpoint tương thích. Nếu phiên bản xử lý đã thay đổi, tạo lượt chạy riêng trên cùng PDF và ghi thay đổi đó.
- [ ] Phân loại các lỗi còn lại thành thiếu danh bạ, tên/mã mơ hồ, sai phạm vi, thiếu bằng chứng PDF hoặc chưa có quy tắc. Xác minh các alias có tần suất cao trước khi thêm vào policy. Giữ trường hợp trùng tuyến ở trạng thái cần rà soát.

**Kiểm chứng.** `python -m pytest tests/test_directory_enrichment.py tests/test_sync.py tests/test_registry.py tests/test_resolver.py tests/test_api.py -q`. Có bảng delta theo từng văn bản và snapshot. Kiểm tra ca cùng tên khác sphere, danh bạ trả thiếu trang và lần đồng bộ lặp lại.

## 4. Hỗ trợ phạm vi nhóm trong backend

**Phụ thuộc.** Bước 1 có quy đổi tập đích. Bước 3 có mã/sphere và đường đồng bộ danh bạ.

- [ ] Bắt đầu bằng nhóm **135 xã phường**, vì 8.106 lượt xã/phường chiếm 70,40% số đích thiếu của Test 1. Bản ghi iDesk ngày 05/11 đã lưu ID nhóm gốc và 135 mã thành viên để đối chiếu. Xác minh snapshot áp dụng trước khi đưa vào ca mới. [Dữ liệu nhóm đã quan sát](../../../var/recipient-coverage/native-groups.json)
- [ ] Mở rộng `sync.py` và `registry.py` để giữ ID nhóm gốc, tenant, sphere, tập mã thành viên, trạng thái đầy đủ và phiên bản. Snapshot đầy đủ mới thay thế tập thành viên. Nếu dữ liệu đổi hoặc thiếu, yêu cầu làm mới và rà soát theo trạng thái thực tế.
- [ ] Trong `resolver.py`, xác định riêng toàn bộ, danh sách cụ thể, nhóm con theo địa bàn, ngoại lệ và tham chiếu tới phụ lục. Dùng node cha khi toàn bộ con thuộc phạm vi. Dùng đơn vị lẻ cho danh sách cụ thể hoặc tập con chưa có nhóm tương đương.
- [ ] Giữ tập đích có thể kiểm chứng theo danh bạ. Bổ sung phần kế hoạch điền tùy chọn trong hợp đồng `outgoing.v1` với nhóm gốc, sphere, tập mã kỳ vọng và phiên bản. Client cũ vẫn đọc kết quả `people`/`units` theo hợp đồng hiện tại.

**Kiểm chứng.** Chạy tests của bước 3 và `tests/test_jobs.py`. Ca 13116/UBND-TD với 9 xã đi đúng phạm vi 9 xã. Ca chọn toàn tỉnh quy đổi theo đủ 135 mã nếu nguồn xác nhận. Thử nhóm ven biển gần trùng tên, danh sách có ngoại lệ và membership đổi làm hết hiệu lực kết quả cũ.

## 5. Điền nhóm có kiểm chứng trên iDesk

**Phụ thuộc.** Hợp đồng kế hoạch điền từ bước 4.

- [ ] Trong userscript, dùng `src/outgoing/idesk.js` để lấy nhóm theo ID gốc và `src/outgoing/form.js` để điền vào đúng trường. Giữ các kiểm tra tenant, văn bản đang mở và version hiện có.
- [ ] Với “135 xã phường”, mở **Nhóm đơn vị trong tỉnh** và chọn đúng nhóm một lần. So tập chip sau khi iDesk bung nhóm với tập kỳ vọng. Chỉ đánh dấu điền xong khi các trường có tập ID/mã đúng.
- [ ] Nếu thiếu nhóm, lệch thành viên, sai trường hoặc thay đổi văn bản giữa chừng, dừng chuẩn bị và trả lý do cho văn thư. Xác minh phần điền thử trên biểu mẫu trước bước xác nhận gửi của người dùng.

**Kiểm chứng.** Trong repo userscript chạy `npm test`, `npm run build` và `npm run verify:outgoing` theo cấu hình dự án. Thử giao diện với toàn nhóm, 9 xã, đổi membership và biểu mẫu đã có chip từ trước.

## 6. Cải thiện các ca trích xuất và suy luận còn thiếu

**Phụ thuộc.** Bước 1 có nhãn PDF và bước 2 có kết quả trích xuất đủ để phân loại lỗi. Tận dụng các lát kiểm thử của bước 4 cho phạm vi nhóm.

- [ ] Trong `extraction.py`, `mentions.py` và `article_references.py`, sửa theo ca có bằng chứng. Ưu tiên danh sách xuống dòng, scan phần Nơi nhận, viết tắt, “Như trên”, “Như Điều N”, phụ lục và `Lưu` theo quy tắc đã xác minh. Kiểm tra cả ca tên người ký xuất hiện trong nội dung.
- [ ] Phân tích các ca thiếu trưởng phòng, PVHCC đích danh và PVHCC nằm trong nhóm. Gắn mỗi đích suy ra từ PDF với trang/đoạn và đường suy luận qua alias, vai trò, nhóm hoặc tham chiếu. Mở rộng “Như trên” theo tập nhận mà cụm này trỏ tới và xác minh thành viên nhóm. Kiểm tra riêng các hồ sơ TTHC/ABTC có bằng chứng luân chuyển qua Trung tâm.
- [ ] Giữ hai tập nguồn độc lập cho 13114/UBND-NC và các ca tương tự. Bộ nhãn PDF phản ánh đích có căn cứ từ tài liệu. Bộ nhãn lịch sử phản ánh đích theo iDesk. Dữ liệu gốc xác nhận quy tắc phát hành từ 17/10/2026 trên 294 ca trong mẫu. Cơ chế 1 được đưa vào phạm vi qua yêu cầu thực hiện kế hoạch. [Dữ liệu phát lại trước đây](../../../var/recipient-improvement-2026-11-05/publication-policy-replay.json)
- [x] Tách policy VPUB có phiên bản để bổ sung Tổ công tác vào Xử lý văn bản đi (`main`) và PVHCC đứng đầu Đơn vị nhận. Với replay lịch sử, dùng `ed.publishedDate` theo giờ Việt Nam và `externalTransfer`. Với văn bản mới, lấy ngày và ý định phát hành ra ngoài từ lựa chọn đã xác nhận cho thao tác hiện tại. Lưu nguồn nghiệp vụ riêng trong kết quả để chấm PDF và tập đích cuối độc lập.

**Kiểm chứng.** `python -m pytest tests/test_extraction.py tests/test_article_references.py tests/test_resolver.py tests/test_recipient_learning.py -q`. Đánh giá theo ba lớp gồm recall của mention PDF, độ đúng resolve trên mentions chuẩn và exact match của tập đích cuối. Cập nhật quy tắc theo lỗi quan sát được trên bộ phát triển/validation.

## 7. Chấm holdout và nghiệm thu

**Phụ thuộc.** Các bước kỹ thuật đã qua kiểm tra và bộ holdout được khóa trước khi chạy.

- [ ] Dùng validation để so từng lát trên cùng tập ca. Báo thứ tự tác động của provider, danh bạ, nhóm và parsing/policy. Phân loại lỗi theo văn bản và theo lượt nhận để một nhóm lớn không che mất số văn bản sai.
- [ ] Khóa code, cấu hình, model/prompt, danh bạ, policy, membership và bộ nhãn trước lần chấm holdout. Báo tử số/mẫu số, precision/recall, exact match, khoảng tin cậy, ca lỗi và ca chưa đủ đáp án. Nếu sửa sau khi xem holdout, lần xác nhận tiếp theo dùng bộ mới chưa dùng để chỉnh.
- [ ] Chạy full suite backend và userscript. Ghi baseline test từ nhánh hiện tại và phân biệt lỗi hồi quy mới với lỗi có sẵn. Chạy riêng bộ ca khó cho gửi thừa do nhóm, nhầm sphere và thay đổi membership. Kết quả điền được kiểm tra ở chế độ chuẩn bị có văn thư rà soát.
- [ ] Chốt mốc theo số đo. Nếu dưới 95%, xếp phần lỗi còn lại theo số văn bản ảnh hưởng và chỉ triển khai tiếp nhánh có bằng chứng cải thiện. Nếu đáp án được xác minh nhưng đầu vào được phép không đủ để suy ra hơn 5% văn bản, cần giải quyết nguồn thông tin thiếu trước khi đặt mốc 95% cho toàn bộ phạm vi. Áp dụng nguyên tắc tương tự cho mốc 99% với ngưỡng 1%.

## Xác minh quy tắc phát hành ngày 06/11/2026

Đã đọc lại 500 tệp `view.cpx` theo danh mục `.tmp/prepared_500_documents.json`. Ghép từng số hiệu và STT với snapshot thẻ đích ngày 05/11. Dùng `ed.publishedDate` để phân ngày phát hành và `ed.externalTransfer` để phân luồng. Kiểm tra Tổ công tác bằng tài khoản đích trong `proInfos` và PVHCC bằng tên đầy đủ cùng vị trí trong `book.receiver`. Sự hiện diện của hai đích khớp với thẻ đích ở cả 500 ca.

| Phạm vi lịch sử | Số văn bản | Có Tổ công tác | Có PVHCC | PVHCC đứng đầu |
| --- | ---: | ---: | ---: | ---: |
| Trước 17/10/2026 | 204 | 0 | 17 | 2 |
| Từ 17/10/2026, phát hành ra ngoài | 294 | 294 | 294 | 294 |
| Từ 17/10/2026, chỉ chuyển nội bộ | 2 | 0 | 0 | 0 |

Cả 294 bản ghi Tổ công tác có `responsibility = main`. Dữ liệu có hai giá trị `externalTransfer`, gồm 2 và 0. Tổng 206 ca ngoài Cơ chế 1 gồm 204 ca trước mốc và 2 ca nội bộ sau mốc. Hai ca phát hành muộn STT 425 và 430 thỏa điều kiện theo thời điểm phát hành thực tế. Ca 13114/UBND-NC phát hành ra ngoài lúc 10:57 ngày 26/10/2026. Quy trình phát hành giải thích hai đích trong lịch sử của ca này.

**PVHCC trước mốc.** Trong 17 ca nhìn thấy trong lịch sử, 8 ca có tên hoặc viết tắt PVHCC ở Kính gửi, Nơi nhận hoặc Lưu. STT 400 đồng thời có danh mục PVHCC. Trong 9 ca khác, 7 ca có cụm chỉ nhóm sở, ban, ngành ở phần nhận trực tiếp hoặc qua “Như trên”. Trang đầu PDF scan STT 367 xác nhận một trong các cụm nhóm đó. Hai ca còn lại là hồ sơ cho phép sử dụng thẻ ABTC. Nội dung hai PDF xác nhận loại thủ tục, còn tuyến hồ sơ qua Trung tâm cần nguồn nghiệp vụ để xác nhận.

**Phạm vi Cơ chế 2.** STT 338 có “Các sở, ban, ngành tỉnh” và danh sách lịch sử đọc được không có PVHCC. STT 350 ghi “Trung tâm PVHCC” trong PDF, nhưng `book.receiver` bị cắt ở “Trung tâm Ph...”. Các ca tương tự cần lấy lại dữ liệu đầy đủ. Có 53 bản ghi dài 4.094 ký tự và kết thúc bằng dấu ba chấm, trong đó 20 bản ghi trước mốc. Một bản ghi khác cùng độ dài cần đối chiếu. Các ca này chưa đủ để kết luận PVHCC vắng mặt hoặc mở rộng mọi cụm sở, ban, ngành thành một nhóm cố định.

**Tác động khi phát lại Cơ chế 1.** Cộng hai đích vào tập dự đoán Test 1 cho đúng 294 ca đủ điều kiện lịch sử, sau đó loại trùng, khôi phục **587 lượt đích khớp**. Trên đúng snapshot thẻ đích cũ, mức bao phủ đổi từ 28,18% lên **31,84%** và số văn bản khớp toàn bộ từ 48 lên **60/500 (12,00%)**. Đây là mô phỏng riêng quy tắc trên dữ liệu cũ theo tên, với các danh sách bị cắt vẫn hiện diện trong mẫu. Kết quả nghiệm thu dùng danh sách đầy đủ theo ID và bộ văn bản mới.

## Các điểm dừng kiểm tra

| Sau bước | Đầu ra cần có |
| --- | --- |
| 1–2 | Manifest và nhãn có nguồn, baseline theo ID hoặc danh sách ca chưa thể chấm, kết quả preflight và báo cáo lượt PDF nhỏ. |
| 3–5 | So sánh danh bạ trước/sau, quy đổi đúng nhóm cha và tập con, bằng chứng iDesk điền đúng các mã kỳ vọng. |
| 6–7 | Báo cáo nguồn suy luận cho các ca còn tranh luận, kết quả holdout khóa và quyết định đạt mốc 95% hoặc 99% dựa trên phép đo. |

## Tình trạng triển khai

- Bộ chấm hỗ trợ snapshot, quy đổi node cha, kiểm tra ID/mã/sphere, phân biệt đích PDF và đích chính sách. Công cụ khóa holdout kiểm tra hash và ngăn trùng dữ liệu phát triển. Các nhãn chưa đầy đủ cần được bổ sung từ iDesk.
- Adapter thử lại đúng model khi bị từ chối vì tham số schema và vẫn xác thực JSON tại backend. Preflight trên cấu hình OpenRouter hiện hành hết thời gian chờ ở cả text và vision. Lượt đọc cục bộ năm PDF thật trả các phần trích xuất có bằng chứng cùng trạng thái partial.
- Backend hỗ trợ nhóm 135, danh sách xã/phường cụ thể và ngoại lệ có thể xác minh. Userscript kiểm tra nhóm theo ID và tập thành viên ở thời điểm điền, theo dõi chip đã thêm theo chính sách và kiểm tra trường người nhận trước khi báo thành công.
- Đã phát lại 500 checkpoint cũ với cùng dữ liệu đầu vào. Kết quả mới khớp 13.200/16.031 lượt đích (82,34%) và 119/500 văn bản (23,80%). Đây là đối chiếu chẩn đoán theo tên. Bản ghi gồm số liệu theo từng lát, danh sách thiếu/thừa và cờ 54 dòng bị cắt hoặc ở sát giới hạn. [Kết quả replay](../../../var/recipient-coverage/replay-after.json)
- Full suite backend có 220 kiểm thử qua và bảy lỗi đối soát Google Sheets trùng baseline. Userscript qua 95 kiểm thử, build và kiểm tra HTTP tích hợp với FastAPI.
- Đã kiểm tra ca mới 13532/UBND-PVHCC ở Sổ văn bản đi. Sổ ghi sáu đơn vị gồm PVHCC. Mục Thông tin liên thông hiển thị mã của năm đơn vị đã nhận và thiếu một dòng tương ứng PVHCC. Nguồn nhãn cần ghi riêng lựa chọn đích trên form và kết quả giao liên thông. Có thể dùng bảng liên thông để xác minh mã giao, nhưng phải đối chiếu với các đích chỉ ghi trong sổ và người nhận nội bộ.
- Bước nghiệm thu vẫn cần khóa bộ văn bản mới được rà nhãn đầy đủ và xác nhận đường chạy provider, rồi chấm trước khi văn thư chỉnh sửa. [Lệnh và định dạng đánh giá](../../evaluation.md)

