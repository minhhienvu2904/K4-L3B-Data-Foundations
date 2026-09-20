# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** G69
**Thành viên:** Trần Quốc Toản · Nguyễn Công Thịnh · Vũ Minh Hiển · Phan Đại Cương
**Ngày:** 20/09/2026

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề & Lý Do Chọn

**Chủ đề:** chính sách đổi trả, bảo hành và quy định người bán/người mua trên sàn thương mại điện tử Tiki. Tiki công bố chính sách chính thức cho cả người mua (hotro.tiki.vn) lẫn nhà bán (hocvien.tiki.vn), có con số, thời hạn và điều kiện cụ thể, nên `metadata_filter` theo `audience` có việc thật để làm. Nội dung được chia theo mục (heading) rõ ràng, phù hợp để so sánh các chiến lược chunking.

**Tại sao nhóm chọn chủ đề này?**

> Chủ đề đổi trả/bảo hành là nhu cầu tra cứu thực tế của cả người mua lẫn người bán trên sàn TMĐT, có sẵn tài liệu công khai (không cần xin phép), số liệu cụ thể (số ngày, điều kiện) giúp dễ kiểm chứng gold answer, và tách biệt rõ ràng theo `audience` (buyer/seller) nên minh hoạt tốt tác dụng của `search_with_filter`.

### Danh sách tài liệu (Data Inventory)

| doc_id                                | audience | Nguồn                                                                                     | document_version     | Ký tự  |
| ------------------------------------- | -------- | ----------------------------------------------------------------------------------------- | -------------------- | ------ |
| buyer-chinh-sach-doi-tra-hoan-tien    | buyer    | hotro.tiki.vn/knowledge-base/post/802-chinh-sach-ve-doi-tra-hang-va-hoan-tien             | effective-2026-07-01 | 11.454 |
| buyer-chinh-sach-bao-hanh             | buyer    | hotro.tiki.vn/knowledge-base/post/772-chinh-sach-bao-hanh-tai-tiki-nhu-the-nao            | effective-2013-03-19 | 3.000  |
| buyer-san-pham-han-che-doi-tra        | buyer    | hotro.tiki.vn/knowledge-base/post/841-nhung-san-pham-nao-toi-khong-the-doi-tra-do-nhu-cau | not-stated           | 1.478  |
| seller-faq-doi-tra-bao-hanh           | seller   | hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/                         | not-stated           | 13.073 |
| seller-fbt-quy-trinh-doi-tra-bao-hanh | seller   | hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/               | not-stated           | 2.640  |

**Data governance checklist:**

- [x] Tập tài liệu chỉ chứa nguồn công khai (trang hỗ trợ chính thức của Tiki), không chứa dữ liệu cá nhân/đăng nhập/nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at` (2026-09-20), `document_version` (hoặc `not-stated` nếu nguồn không nêu) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata    | Kiểu                      | Ví dụ giá trị                                                                                     | Tại sao hữu ích cho retrieval?                                                                                                                        |
| ------------------ | ------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `audience`         | string (`buyer`/`seller`) | `seller`                                                                                          | Cho phép `search_with_filter` lọc đúng nhóm người dùng trước khi tính similarity, tránh trả lời chính sách buyer cho câu hỏi của seller và ngược lại. |
| `source_url`       | string (URL)              | `https://hotro.tiki.vn/...`                                                                       | Dùng để trích dẫn nguồn trong câu trả lời của agent, tăng khả năng kiểm chứng thông tin.                                                              |
| `retrieved_at`     | date (YYYY-MM-DD)         | `2026-09-20`                                                                                      | Ghi nhận thời điểm crawl để đánh giá độ mới của thông tin khi chính sách thay đổi.                                                                    |
| `document_version` | string                    | `effective-2026-07-01` / `not-stated`                                                             | Giúp phân biệt phiên bản chính sách khi Tiki cập nhật điều khoản theo thời gian.                                                                      |
| `category`         | string                    | `returns-refund-policy`, `warranty-policy`, `returns-restricted-products`, `returns-warranty-faq` | Cho phép lọc mịn hơn theo loại chính sách cụ thể (đổi trả / bảo hành / danh mục hạn chế) nếu cần mở rộng filter sau này.                              |
| `platform`         | string                    | `tiki`                                                                                            | Hữu ích nếu sau này mở rộng corpus sang nhiều sàn TMĐT khác nhau, tránh trộn lẫn chính sách giữa các nền tảng.                                        |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(body, chunk_size=300)` trên 2 tài liệu thật của nhóm:

| Tài liệu                                          | Chiến lược   | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không?                                                                                          |
| ------------------------------------------------- | ------------ | -------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| buyer-chinh-sach-doi-tra-hoan-tien (11.454 ký tự) | fixed_size   | 43             | 295.7             | Kém — cắt cứng theo ký tự, có thể chia đôi một câu hoặc một điều khoản.                                           |
| buyer-chinh-sach-doi-tra-hoan-tien                | by_sentences | 40             | 283.6             | Trung bình — giữ trọn câu nhưng không biết ranh giới heading, có thể gộp câu từ 2 mục khác nhau.                  |
| buyer-chinh-sach-doi-tra-hoan-tien                | recursive    | 57             | 199.3             | Khá — ưu tiên tách theo đoạn/dòng nên ít cắt giữa câu hơn fixed_size, nhưng chunk nhỏ hơn (199 ký tự) nên dễ vụn. |
| seller-faq-doi-tra-bao-hanh (13.073 ký tự)        | fixed_size   | 49             | 296.2             | Kém — tương tự, dễ cắt giữa câu hỏi/câu trả lời trong FAQ.                                                        |
| seller-faq-doi-tra-bao-hanh                       | by_sentences | 35             | 370.6             | Trung bình — chunk dài hơn (nhiều FAQ ngắn gộp lại), có thể trộn nội dung của 2 câu hỏi khác nhau vào 1 chunk.    |
| seller-faq-doi-tra-bao-hanh                       | recursive    | 71             | 182.4             | Khá — nhưng file FAQ có nhiều mục ngắn nên recursive tạo khá nhiều chunk nhỏ.                                     |

**Nhận xét:** cả 3 chiến lược baseline đều không biết khái niệm "heading" nên có thể cắt ngang một câu hỏi FAQ hoặc một điều khoản — đây chính là lý do nhóm cần thử thêm chiến lược **chunk theo heading** (xem bên dưới).

### Chiến lược của từng thành viên

**Thành viên 1 — Trần Quốc Toản**

- **Loại chiến lược:** HeadingChunker (custom)
- **Backend embedding:** MockEmbedder (MD5-based)
- **Mô tả & lý do chọn:** Corpus là các trang chính sách/FAQ có heading `##`/`###` rất rõ ràng (mỗi câu hỏi FAQ hoặc mỗi điều khoản là một heading), nên chunk theo heading giữ được trọn vẹn một ý/một điều khoản trong một chunk; heading được gắn lại vào các mảnh con khi section quá dài để không mất ngữ cảnh "đang nói về heading nào".
- **Code snippet:**

```python
class HeadingChunker:
    HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+.*$")

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        matches = list(self.HEADING_RE.finditer(text))
        # ... tách theo từng heading, hạ recursive nếu section dài,
        # gắn lại heading vào mọi mảnh con.
```

Kết quả trên corpus: **116 chunk** / 5 file, avg_length ~ 280-310 ký tự (xem `ket_qua_benchmark.txt`). 1/5 câu có chunk liên quan ở top-1.

**Thành viên 2 — Nguyễn Công Thịnh**

- **Loại chiến lược:** **Semantic Chunking** (custom, dựa trên embedding similarity giữa các câu).
- **Backend embedding:** MockEmbedder (được nhắc trực tiếp ở mục 4: _"cần dùng embedding đa ngữ thật như `LocalEmbedder`"_).
- **Ý tưởng thuật toán:** tách văn bản thành từng câu (giống `SentenceChunker`), sau đó tính embedding của từng câu và đo cosine similarity giữa câu hiện tại với câu liền trước. Nếu similarity vẫn cao (trên một ngưỡng, ví dụ 0.5) thì gộp câu đó vào chunk đang mở vì được xem là cùng một mạch ý; nếu similarity giảm mạnh (dấu hiệu đổi chủ đề) thì đóng chunk hiện tại và mở chunk mới bắt đầu từ câu đó. Chunk cũng bị đóng bắt buộc nếu đã đạt `chunk_size` tối đa dù similarity còn cao, để tránh chunk phình quá lớn.
- **Mô tả & lý do chọn:** khác với `RecursiveChunker` (cắt theo ký tự phân cách cố định như `\n`, `. `) hay `HeadingChunker` (cắt theo cấu trúc heading có sẵn), Semantic Chunking chọn ranh giới chunk dựa trên **nội dung thực sự** — hữu ích với các đoạn văn dài không có heading rõ ràng nhưng vẫn chuyển ý giữa chừng (ví dụ trong `buyer-chinh-sach-doi-tra-hoan-tien` có nhiều đoạn liệt kê nhiều điều kiện liên tiếp mà không tách heading). Nhược điểm lớn nhất là chất lượng ranh giới hoàn toàn phụ thuộc vào embedding: với `MockEmbedder`, similarity giữa 2 câu liên tiếp gần như ngẫu nhiên (đã chứng minh ở `REPORT_CANHAN.md` mục 4 của Thịnh), nên ranh giới chunk tạo ra không đáng tin cậy — đây có thể là lý do kết quả retrieval của Thịnh (2/5) không vượt trội hơn nhiều so với các chiến lược "ngây thơ" hơn dù về lý thuyết Semantic Chunking tinh vi hơn.
- **Kết quả:** 2/5 câu có chunk liên quan trong top-3 (câu 2 và câu 5).

**Thành viên 3 — Vũ Minh Hiển**

- **Loại chiến lược:** **Keyword-based Chunking** (custom, gom đoạn văn theo mật độ/xuất hiện của từ khóa nghiệp vụ).
- **Backend embedding:** MockEmbedder.
- **Ý tưởng thuật toán:** định nghĩa trước một danh sách từ khóa nghiệp vụ đặc trưng của corpus (ví dụ: "đổi trả", "bảo hành", "hoàn tiền", "video đóng gói", "Seller Center", "đồng kiểm"...). Quét văn bản theo câu/đoạn; mỗi khi gặp câu chứa một từ khóa **mới** (khác với từ khóa đang "chủ đề" của chunk hiện tại) thì đóng chunk cũ và mở chunk mới bắt đầu từ đó — về bản chất coi mỗi cụm từ khóa nghiệp vụ như một "heading ẩn" để tách đoạn, kể cả khi văn bản gốc không có heading Markdown tường minh.
- **Mô tả & lý do chọn:** phù hợp với đặc điểm corpus là văn bản chính sách có thuật ngữ nghiệp vụ lặp lại nhất quán (cùng một cụm từ như "video đóng gói" hay "Seller Center" xuất hiện ở nhiều chỗ khi nói về cùng một quy trình), nên nhóm theo từ khóa giúp mỗi chunk tập trung đúng một chủ đề nghiệp vụ mà không cần dựa vào cấu trúc heading của tài liệu (khác `HeadingChunker`) hay embedding similarity (khác Semantic Chunking của Thịnh) — chunker này nhẹ, dễ giải thích, không cần tính embedding khi chunk. Nhược điểm: chất lượng phụ thuộc hoàn toàn vào danh sách từ khóa được định nghĩa thủ công — nếu câu hỏi dùng từ đồng nghĩa không có trong danh sách (ví dụ hỏi "quay clip mở hàng" thay vì "video đóng gói") thì chunker không nhận diện được ranh giới đúng, và việc bảng của Hiển không dùng `metadata_filter` (không có cột filter trong báo cáo) càng làm giảm độ chính xác vì phải tìm trên toàn bộ 5 file thay vì thu hẹp theo `audience`.
- **Kết quả:** 1/5 câu có chunk liên quan trong top-3 (tự báo cáo).

**Thành viên 4 — Phan Đại Cương**

- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)`.
- **Backend embedding:** **`gemini-embedding-001` (embedding thật, không dùng Mock)** — điểm khác biệt lớn nhất so với 3 thành viên còn lại.
- **Mô tả & lý do chọn:** Recursive chunking giữ cấu trúc đoạn/tiêu đề tốt hơn cắt cố định; kết hợp với embedding thật cho phép đánh giá retrieval theo đúng ngữ nghĩa thay vì chỉ dựa vào trùng khớp ký tự như Mock.
- **Kết quả:** **116 → 85 chunk** (ít hơn do gộp đoạn hiệu quả hơn), **5/5 câu có chunk liên quan trong top-3**, điểm score thực tế cao (0.83–0.90) — vượt trội hoàn toàn so với 3 thành viên dùng Mock.

### So Sánh Giữa Các Thành Viên

| Thành viên         | Chiến lược                                 | Embedding                | Điểm truy xuất (top-3 liên quan / 5) | Điểm mạnh                                                                                            | Điểm yếu                                                                                        |
| ------------------ | ------------------------------------------ | ------------------------ | ------------------------------------ | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Trần Quốc Toản     | HeadingChunker                             | Mock                     | 1/5                                  | Mỗi chunk giữ nguyên một điều khoản/câu hỏi FAQ, dễ trích dẫn nguồn chính xác                        | Score không phản ánh đúng ngữ nghĩa nên nhiều câu bị lệch section dù đúng chủ đề                |
| Nguyễn Công Thịnh  | Semantic Chunking                          | Mock                     | 2/5                                  | Ranh giới chunk dựa trên đổi ý/chủ đề thực sự (về lý thuyết), không phụ thuộc heading có sẵn         | Với Mock, similarity giữa các câu gần như ngẫu nhiên nên ranh giới tạo ra không đáng tin cậy    |
| Vũ Minh Hiển       | Keyword-based Chunking (không dùng filter) | Mock                     | 1/5                                  | Nhẹ, dễ giải thích, không cần tính embedding lúc chunk; đúng chủ đề ở câu 4 (top-1 khớp danh mục)    | Phụ thuộc hoàn toàn vào danh sách từ khóa thủ công; không lọc `audience` nên tìm trên cả 5 file |
| **Phan Đại Cương** | **RecursiveChunker**                       | **gemini-embedding-001** | **5/5**                              | Embedding thật hiểu đúng ngữ nghĩa tiếng Việt, mọi câu đều có chunk gold ở top-1 (trừ câu 1 ở top-2) | Cần API key/chi phí gọi model thật; số lượng thử nghiệm bị giới hạn bởi rate limit/chi phí      |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> Kết quả của nhóm cho thấy rõ: **chất lượng embedding quan trọng hơn nhiều so với chiến lược chunking**, ít nhất ở quy mô thử nghiệm này. Ba thành viên dùng `MockEmbedder` (HeadingChunker, và 2 chiến lược chưa xác định rõ) đều chỉ đạt 1-2/5 câu có chunk liên quan, bất kể chunk có giữ nguyên ngữ cảnh heading tốt đến đâu — vì Mock không hiểu ngữ nghĩa tiếng Việt (đã chứng minh bằng số liệu ở `REPORT_CANHAN.md` mục 4 của từng người: câu đồng nghĩa vẫn có thể ra điểm âm). Ngược lại, Phan Đại Cương dùng `RecursiveChunker` — một chiến lược "phổ thông", không đặc thù cho tài liệu có heading — nhưng kết hợp với embedding thật (`gemini-embedding-001`) lại đạt 5/5. Kết luận: **với corpus có cấu trúc heading rõ như của nhóm, HeadingChunker/RecursiveChunker đều là lựa chọn hợp lý về mặt giữ ngữ cảnh, nhưng để retrieval thực sự chính xác thì bắt buộc phải dùng embedding thật thay vì Mock.**

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Gold Answer

| #   | Câu hỏi                                                                                           | Gold Answer                                                                                                                                                                                                                            | Chunk chứa thông tin                                                                                |
| --- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1   | Thời gian hỗ trợ đổi trả hàng tại Tiki là bao nhiêu ngày?                                         | 30 ngày kể từ lúc nhận hàng thành công (áp dụng từ đơn hàng đặt từ 15/04/2024); riêng Thiết bị số - Phụ kiện số, Điện gia dụng do Tiki Trading bán được đổi trả trong 365 ngày nếu lỗi kỹ thuật.                                       | `buyer-chinh-sach-doi-tra-hoan-tien` — mục "Chính sách đổi trả – Thời gian hỗ trợ đổi trả tại Tiki" |
| 2   | Sản phẩm bảo hành gửi về Tiki thì mất bao lâu để nhận lại? (filter `buyer`)                       | Khoảng 15-30 ngày tùy linh kiện thay thế (không tính thời gian vận chuyển); riêng sản phẩm Apple dự kiến 30-60 ngày.                                                                                                                   | `buyer-chinh-sach-bao-hanh` — mục "Sau bao lâu tôi có thể nhận lại sản phẩm bảo hành?"              |
| 3   | Nhà Bán cần lưu trữ video đóng gói hàng hóa trong bao lâu? (filter `seller`)                      | Tối thiểu 45 ngày (30 ngày kể từ khi giao hàng thành công cộng thêm thời gian luân chuyển giao hàng và thu hồi sản phẩm).                                                                                                              | `seller-faq-doi-tra-bao-hanh` — mục "Nhà Bán cần lưu trữ video đóng gói hàng hóa trong bao lâu?"    |
| 4   | Những nhóm sản phẩm nào không được đổi trả theo nhu cầu?                                          | Ví dụ: đồ lót/đồ bơi, nước hoa, trang sức, báo/tạp chí và CD/DVD, hoa tươi/cây cảnh, voucher-dịch vụ, thực phẩm tươi sống/đông lạnh, hàng giao từ nước ngoài, quà tặng kèm.                                                            | `buyer-san-pham-han-che-doi-tra` — mục "Danh mục sản phẩm không áp dụng đổi - trả theo nhu cầu"     |
| 5   | Quy trình Nhà Bán xử lý khi nhận lại hàng trả từ khách hàng gồm những bước nào? (filter `seller`) | Khách đóng gói trả về theo hướng dẫn; Nhà Bán khi nhận hàng từ đối tác vận chuyển phải đồng kiểm, quay clip mở sản phẩm; nếu hàng trả về lỗi/hư hỏng/sai sản phẩm thì giữ hàng, giữ clip và khiếu nại tại Seller Center để Tiki xử lý. | `seller-faq-doi-tra-bao-hanh` — mục "Nhà Bán nên làm gì khi nhận kiện hàng trả từ khách hàng?"      |

### Tổng hợp chất lượng truy xuất của nhóm

| #   | Câu hỏi                                  | Toản<br>HeadingChunker+Mock | Thịnh<br>Semantic+Mock         | Hiển<br>Keyword(no filter)+Mock | **Cương**<br>**Recursive+gemini** | Chiến lược tốt nhất cho câu này                    |
| --- | ---------------------------------------- | --------------------------- | ------------------------------ | ------------------------------- | --------------------------------- | -------------------------------------------------- |
| 1   | Thời gian đổi trả                        | Không                       | Không                          | Không                           | **Có** (top-2, 0.85)              | Cương (Recursive + gemini) — duy nhất đúng         |
| 2   | Thời gian bảo hành (filter buyer)        | Không                       | Có (top-3, hạng 2)             | Không                           | **Có** (top-1, 0.88)              | Cương; Thịnh cũng đạt top-3                        |
| 3   | Thời gian lưu video (filter seller)      | Không                       | Không                          | Không                           | **Có** (top-1, 0.89)              | Cương — duy nhất đúng                              |
| 4   | Danh mục không đổi trả                   | Không                       | Một phần (đúng file, sai đoạn) | **Có** (top-1, 0.23)            | **Có** (top-1, 0.88)              | Hiển và Cương đều đúng top-1                       |
| 5   | Quy trình xử lý hàng trả (filter seller) | **Có** (top-1, 0.376)       | Có (top-3, hạng 3)             | Có (một phần, top-1)            | **Có** (top-1, đầy đủ chi tiết)   | Cương đầy đủ nhất; cả 4 người đều tìm ra file đúng |

**Tổng số câu có chunk liên quan trong top-3, theo từng người:** Toản 1/5 · Thịnh 2/5 · Hiển 1/5 · **Cương 5/5**.

**Lọc metadata có giúp ích không? Ở câu hỏi nào?**

> Lọc `audience` giúp loại đúng các tài liệu không liên quan trước khi tính similarity (ví dụ câu 3, 5 chỉ tìm trong 2 file seller thay vì cả 5 file), giảm nhiễu về mặt tập ứng viên. Tuy nhiên nó **không giải quyết được vấn đề chọn sai section trong cùng file** khi dùng Mock — như câu 2 và 3 cho thấy ở báo cáo của Toản, dù đã lọc đúng audience, top-1 vẫn là chunk sai chủ đề. So sánh giữa Hiển (không lọc) và Toản (có lọc), cả hai đều chỉ đạt 1/5 — cho thấy ở dữ liệu này, lọc metadata một mình không đủ để bù đắp cho một embedding không hiểu ngữ nghĩa. Ngược lại, kết quả của Cương (5/5, dùng embedding thật) cho thấy khi embedding đã đủ tốt, metadata filter mới thực sự phát huy tác dụng "thu hẹp đúng vùng tìm kiếm" thay vì phải gánh luôn việc "hiểu đúng nội dung".

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích hay nhất nhóm sẽ trình bày:**

> - MockEmbedder (MD5-based) cho điểm similarity gần như ngẫu nhiên: hai câu hỏi cùng nghĩa (ví dụ "đổi trả trong bao lâu" diễn đạt 2 cách) có thể có score âm, trong khi hai câu không liên quan lại có score dương — chứng minh rõ giới hạn của mock embedding bằng số liệu thật (xem `REPORT_CANHAN.md` mục 4 của mỗi thành viên).
> - Corpus có 2 giá trị `audience` (buyer/seller) tách biệt rõ ràng giúp metadata filter thu hẹp không gian tìm kiếm hiệu quả, nhưng tự nó không đủ để bù cho một embedding kém — các thành viên dùng Mock (dù có/không dùng filter) đều chỉ đạt 1-2/5 câu đúng.
> - **Bằng chứng rõ ràng nhất của cả nhóm:** cùng corpus, cùng bộ 5 câu hỏi, người duy nhất dùng embedding thật (`gemini-embedding-001`, chiến lược RecursiveChunker) đạt 5/5 câu có chunk liên quan trong top-3, trong khi 3 người dùng MockEmbedder (chiến lược chunk khác nhau) chỉ đạt 1-2/5. Đây là bằng chứng thực nghiệm trực tiếp rằng **chất lượng embedding quyết định retrieval nhiều hơn việc chọn đúng chiến lược chunking.**

**Bài học rút ra khi so sánh trong nhóm:**

> Bài học lớn nhất của nhóm là: chunking tốt là điều kiện _cần_ nhưng không _đủ_ cho RAG hoạt động tốt — nếu embedding không hiểu ngữ nghĩa, chunk có mạch lạc đến đâu cũng khó được xếp hạng đúng. Bốn thành viên dùng 4 chiến lược khác hẳn nhau về triết lý (HeadingChunker bám cấu trúc heading, Semantic Chunking bám embedding similarity giữa câu, Keyword-based Chunking bám từ khóa nghiệp vụ, RecursiveChunker cắt theo separator thông thường), nhưng 3 người dùng MockEmbedder đều chỉ đạt 1-2/5 dù độ "tinh vi" của chiến lược rất khác nhau — thậm chí Semantic Chunking (lý thuyết tinh vi nhất, dựa trên similarity) cũng không vượt trội vì chính similarity đó được tính từ Mock. Trong khi đó RecursiveChunker — chiến lược đơn giản nhất trong 4 — lại đạt 5/5 chỉ vì đi kèm embedding thật. Điều này cho nhóm bài học rõ ràng: **đầu tư vào chất lượng embedding mang lại lợi ích lớn hơn nhiều so với đầu tư vào việc làm chunking tinh vi hơn**, ít nhất ở quy mô corpus của nhóm.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu?**

> Nếu làm lại, nhóm sẽ: (1) thống nhất từ đầu dùng `LocalEmbedder` hoặc `gemini-embedding-001` như Cương đã thử, để so sánh các chiến lược chunking công bằng trên nền embedding thật thay vì Mock; (2) yêu cầu mỗi thành viên ghi rõ tên chiến lược + backend embedding ngay trong bảng kết quả mục 5; (3) thêm trường metadata `category` vào bộ query để kiểm tra filter mịn hơn ngoài `audience`.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá                                                                              |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10                                                                                       |
| Thiết kế chiến lược (Strategy Design)    | 15 / 15 _(4 chiến lược khác biệt rõ ràng về triết lý: heading, semantic, keyword, recursive)_ |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 _(có đối chiếu Mock vs. embedding thật, phân tích nguyên nhân rõ ràng)_                |
| Thuyết trình (Demo)                      | 0 / 5 _(chấm sau buổi demo thật với giảng viên)_                                                    |
| **Tổng phần nhóm**                       | **34 / 40**                                                                        |
