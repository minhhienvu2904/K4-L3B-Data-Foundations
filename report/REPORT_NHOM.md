# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhóm 7 — Tiki Policy Retrieval
**Thành viên:** [Tên các thành viên trong nhóm]
**Ngày:** 2026-09-20

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

**Thành viên 1 — [Tên]**

- **Loại chiến lược:** HeadingChunker (custom)
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

Kết quả trên corpus: **114 chunk** / 5 file, avg_length ~ 280-310 ký tự (xem `ket_qua_benchmark.txt`).

> _Viết sau khi có đủ số liệu từ các thành viên khác. Gợi ý: với corpus chính sách/FAQ có heading rõ ràng như của nhóm, HeadingChunker về lý thuyết giữ ngữ cảnh tốt nhất (mỗi chunk = một điều khoản/một câu hỏi trọn vẹn), nhưng vì đang test bằng MockEmbedder nên chưa thể hiện rõ ưu thế qua điểm số — cần embedding thật để so sánh công bằng._

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

| #   | Câu hỏi                                  | Chiến lược tốt nhất cho câu này         | Có chunk liên quan trong top-3? | Ghi chú                                                                                |
| --- | ---------------------------------------- | --------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------- |
| 1   | Thời gian đổi trả                        | HeadingChunker | Với HeadingChunker: Không       | Top-3 toàn nói về bảo hành/xử lý khiếu nại, không chunk nào chứa "30 ngày"             |
| 2   | Thời gian bảo hành (filter buyer)        | HeadingChunker                                | Với HeadingChunker: Không       | Top-1 lạc đề (danh mục hàng không đổi trả) dù đã lọc đúng audience                     |
| 3   | Thời gian lưu video (filter seller)      | HeadingChunker                                | Với HeadingChunker: Không       | Đáp án đúng nằm trong cùng file `seller-faq-doi-tra-bao-hanh` nhưng bị xếp ngoài top-3 |
| 4   | Danh mục không đổi trả                   | HeadingChunker                                | Với HeadingChunker: **Có**       | Top-1 trùng đúng danh mục sản phẩm không đổi trả theo nhu cầu                          |
| 5   | Quy trình xử lý hàng trả (filter seller) | HeadingChunker                                | Với HeadingChunker: **Có**      | Top-1 đúng file, sát chủ đề, nhưng chưa chứa đủ chi tiết "đồng kiểm + quay clip"   |

**Lọc metadata có giúp ích không? Ở câu hỏi nào?**

> Lọc `audience` giúp loại đúng các tài liệu không liên quan trước khi tính similarity (ví dụ câu 3, 5 chỉ tìm trong 2 file seller thay vì cả 5 file), giảm nhiễu về mặt tập ứng viên. Tuy nhiên nó **không giải quyết được vấn đề chọn sai section trong cùng file** — như câu 2 và 3 cho thấy, dù đã lọc đúng audience, top-1 vẫn là chunk sai chủ đề vì gốc rễ vấn đề là `MockEmbedder` không hiểu ngữ nghĩa, không phải do filter. Điều này cho thấy metadata filter thu hẹp không gian tìm kiếm rất tốt, nhưng chất lượng embedding mới quyết định độ chính xác cuối cùng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích hay nhất nhóm sẽ trình bày:**

> - MockEmbedder (MD5-based) cho điểm similarity gần như ngẫu nhiên: hai câu hỏi cùng nghĩa (ví dụ "đổi trả trong bao lâu" diễn đạt 2 cách) có thể có score âm, trong khi hai câu không liên quan lại có score dương — chứng minh rõ giới hạn của mock embedding bằng số liệu thật (xem `REPORT_CANHAN.md` mục 4).
> - Corpus có 2 giá trị `audience` (buyer/seller) tách biệt rõ ràng giúp metadata filter thu hẹp không gian tìm kiếm hiệu quả, dù chưa cải thiện được độ chính xác trong cùng file.
> - Chunk theo heading giữ nguyên trọn vẹn từng điều khoản/câu hỏi FAQ — về lý thuyết tốt cho loại tài liệu chính sách/FAQ có cấu trúc heading rõ, nhưng cần embedding thật để chứng minh ưu thế bằng số liệu.

**Bài học rút ra khi so sánh trong nhóm:**

> Dù đã filter đúng `audience`, top-3 vẫn có thể bị lệch vì `MockEmbedder` không hiểu ngữ nghĩa và score dựa trên hash, không dựa trên sự liên quan thực sự. Vì vậy, `count` / `avg_length` / độ mạch lạc của chunk vẫn là chỉ số đáng tin cậy trong bài lab khi embedding không thật, còn độ chính xác cuối cùng cần embedding thực để đánh giá đúng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu?**

> Nếu làm lại, nhóm sẽ bật embedder thật hoặc tối thiểu dùng local multilingual embedding để kiểm tra xem sự lệch về section còn tồn tại hay không; đồng thời, bổ sung metadata `category` và thử filter theo `category + audience` để giảm nhiễu khi cùng một file có nhiều chủ đề.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá                              |
| ---------------------------------------- | --------------------------------------------- |
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10                                       |
| Thiết kế chiến lược (Strategy Design)    | / 15 _(điền sau khi đủ dữ liệu 3 thành viên)_ |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10                                        |
| Thuyết trình (Demo)                      | / 5                                           |
| **Tổng phần nhóm**                       | **/ 40**                                      |
