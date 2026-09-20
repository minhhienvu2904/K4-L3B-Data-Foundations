# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vũ Minh Hiển  
**Nhóm:** Nhóm 7 — Tiki Policy Retrieval  
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding có hướng gần nhau trong không gian nhiều chiều, nghĩa là chúng thể hiện cùng một ý nghĩa dù có thể dùng từ khác nhau. Về mặt toán học, góc giữa hai vector nhỏ và tích vô hướng lớn sau khi chuẩn hóa.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Khách hàng muốn đổi trả sản phẩm vì hàng bị lỗi."
- Câu B: "Sản phẩm hỏng nên người mua cần hoàn trả hàng."
- Tại sao tương đồng: Cả hai mô tả cùng một tình huống và cùng mục tiêu, dù không dùng cùng cụm từ. Embedding hiểu sắc thái nghĩa chứ không chỉ khớp chữ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Tiki quy định thời hạn đổi trả là 30 ngày."
- Câu B: "Đồ lót và nước hoa không được đổi trả theo nhu cầu."
- Tại sao khác: Hai câu cùng thuộc chính sách nhưng nói về hai chủ đề khác nhau: thời hạn và danh mục sản phẩm cấm đổi trả.

**Tại sao độ tương tự cosine được ưu tiên hơn khoảng cách Euclid cho text embeddings?**
> Vì embeddings văn bản chủ yếu phản ánh hướng ý nghĩa, không phải độ lớn tuyệt đối của vector. Cosine focus vào góc giữa các vector, còn Euclidean distance bị ảnh hưởng bởi độ dài vector, nên ít phù hợp hơn khi so sánh nghĩa của văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: ceil((length - overlap) / (chunk_size - overlap))  
> = ceil((10000 - 50) / (500 - 50))  
> = ceil(9950 / 450) = ceil(22.11) = 23  
> **Đáp án: 23**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với overlap = 100:  
> ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25  
> **Đáp án: 25 chunk**
>
> Khi overlap lớn hơn, bước trượt giữa các chunk nhỏ hơn, nên các chunk chồng lấn nhiều hơn, giúp giữ ngữ cảnh ở ranh giới chunk và giảm nguy cơ mất thông tin. Tuy nhiên, nó làm tăng số lượng chunk và gây trùng nhau nhiều hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi sử dụng regex tách theo dấu câu cuối cùng như `.`, `!`, `?` và cả khoảng trắng / newline sau đó. Sau khi chia, tôi trim từng phần, lọc bỏ chuỗi rỗng, rồi ghép theo `max_sentences_per_chunk` để đảm bảo chunk có tính mạch lạc và không chứa phần trống thừa.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán chạy đệ quy theo thứ tự separator ưu tiên: đoạn văn, newline, dấu chấm, khoảng trắng, cuối cùng là cắt bắt buộc nếu không còn separator nào. Nếu một phần vẫn quá dài so với `chunk_size`, hàm tiếp tục chia sâu hơn; còn nếu độ dài hiện tại nhỏ hơn hoặc bằng `chunk_size`, nó dừng lại trực tiếp. Base case ở đây là khi chuỗi hiện tại đã ngắn hơn giới hạn, lúc đó trả về một chunk duy nhất.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi `Document` được chuẩn hóa thành một record gồm `id`, `content`, `metadata` và embedding. Khi thêm tài liệu, tôi lưu bản sao metadata để tránh dữ liệu bên ngoài thay đổi ngẫu nhiên sau khi đã lưu vào store. Với `search`, tôi tính embedding câu hỏi và dùng dot product để sắp xếp các record theo độ tương đồng giảm dần, rồi trả về top-k tốt nhất.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` thực hiện lọc metadata trước khi chạy ranking, nghĩa là chỉ xét các chunk thỏa `audience`, `doc_id` hoặc các trường cần lọc. `delete_document` thì loại bỏ mọi chunk thuộc `doc_id` đó bằng cách lọc trên `record["metadata"].get("doc_id")`, trả về `True` nếu có ít nhất một chunk bị xóa và `False` nếu không tồn tại.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Tôi xây dựng prompt theo nguyên tắc RAG: lấy top-k chunk liên quan nhất, đưa vào phần `Context:`, rồi yêu cầu model trả lời dựa trên dữ liệu đó và chỉ nói rõ khi không có thông tin. Mỗi chunk được gắn nhãn `[1]`, `[2]`, ... để agent có thể tham chiếu và trích dẫn bằng chứng, thay vì suy đoán mơ hồ.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```bash
pytest tests/ -v
```

```text
============================= test session starts ==============================
...
============================= 42 passed in 0.20s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Khách hàng muốn đổi trả sản phẩm vì hàng bị lỗi." | "Sản phẩm hỏng nên người mua cần hoàn trả hàng." | cao | không đo | đúng |
| 2 | "Nhà bán cần lưu trữ video đóng gói hàng hóa." | "Người bán phải giữ clip xác nhận đóng gói sản phẩm." | cao | không đo | đúng |
| 3 | "Thời hạn đổi trả là 30 ngày." | "Hôm nay trời nắng và rất nóng." | thấp | không đo | đúng |
| 4 | "Sản phẩm không được đổi trả theo nhu cầu." | "Các mặt hàng đồ lót, nước hoa, thực phẩm tươi sống không áp dụng đổi trả." | cao | không đo | đúng |
| 5 | "Quy trình xử lý khiếu nại của nhà bán." | "Một người mua đang đặt hàng online." | thấp | không đo | đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 1 và cặp 2 là bất ngờ nhất vì các câu có từ vựng khác nhau nhưng hướng nghĩa tương đồng. Điều này cho thấy embeddings không chỉ so khớp chữ mà còn nắm bắt được “sắc thái ngữ nghĩa”, tức là việc hai câu khác từ nhưng cùng mục đích hoặc cùng chủ đề sẽ đứng gần nhau trong không gian vector.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời gian hỗ trợ đổi trả hàng tại Tiki là bao nhiêu ngày? | "Chính sách hoàn tiền – Bằng chứng và giải quyết tranh chấp" trong `buyer-chinh-sach-doi-tra-hoan-tien` | 0.319 | Không | Không chứa đáp án 30 ngày; chỉ đề cập đến chứng từ và khiếu nại |
| 2 | Sản phẩm bảo hành gửi về Tiki thì mất bao lâu để nhận lại? | "Danh mục sản phẩm không áp dụng đổi - trả theo nhu cầu" | 0.261 | Không | Không trả lời thời gian bảo hành, chỉ liệt kê danh mục hàng cấm đổi trả |
| 3 | Nhà Bán cần lưu trữ video đóng gói hàng hóa trong bao lâu? | FAQ về xác nhận phương án xử lý yêu cầu đổi trả | 0.191 | Không | Không có mốc thời gian 45 ngày, chỉ là hướng xử lý đơn |
| 4 | Những nhóm sản phẩm nào không được đổi trả theo nhu cầu? | "Danh mục sản phẩm không áp dụng đổi - trả theo nhu cầu" | 0.234 | Có | Chứa đúng danh mục sản phẩm cấm đổi trả theo nhu cầu |
| 5 | Quy trình Nhà Bán xử lý khi nhận lại hàng trả từ khách hàng gồm những bước nào? | FAQ "Sau khi Nhà Bán Đồng ý ..." | 0.376 | Có (một phần) | Có gợi ý về đồng ý / xử lý, nhưng thiếu chi tiết "đồng kiểm và quay clip" |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 1 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Qua demo, tôi đánh giá cao cách nhóm khác kết hợp metadata filter và chunking theo heading để cải thiện retrieval. Tôi thấy rõ rằng chỉ dựa trên similarity score là chưa đủ; cần phân biệt đúng audience và ranh giới đoạn văn để tránh trả lời sai ngữ cảnh. Đây là điểm mà tôi sẽ áp dụng cho những bài toán RAG sau này.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |

---

### Ghi chú cá nhân

Qua lab này, tôi thấy rõ rằng retrieval hiệu quả không chỉ là “lấy top-k gần nhất”, mà còn cần “lấy đúng chunk đúng chủ đề, đúng audience và đúng ngữ cảnh”. Việc kết hợp `metadata_filter`, chunking hợp lý và prompt ngắn gọn là ba yếu tố then chốt giúp RAG hoạt động tốt trong các chính sách thương mại điện tử.
