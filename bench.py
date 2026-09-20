"""Run a reproducible retrieval benchmark over the Tiki policy corpus.

Change only ``CHUNKER`` when comparing chunking strategies.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from src import Document, EmbeddingStore, HeadingChunker, _mock_embed


CORPUS_DIR = Path("data/chinh-sach-doi-tra-tiki")
CHUNKER = HeadingChunker(chunk_size=500)

# These are the five questions and source-grounded gold answers documented in
# report/REPORT_NHOM.md.  ``metadata_filter`` is deliberately applied before
# retrieval, so buyer/seller policies cannot occupy top-k slots for each other.
BENCHMARKS = [
    {
        "question": "Thời gian hỗ trợ đổi trả hàng tại Tiki là bao nhiêu ngày?",
        "gold": "30 ngày từ khi nhận hàng thành công; một số sản phẩm Tiki Trading lỗi kỹ thuật có 365 ngày.",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "Sản phẩm bảo hành gửi về Tiki thì mất bao lâu để nhận lại?",
        "gold": "15–30 ngày, riêng Apple dự kiến 30–60 ngày.",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "Nhà Bán cần lưu trữ video đóng gói hàng hóa trong bao lâu?",
        "gold": "Tối thiểu 45 ngày.",
        "metadata_filter": {"audience": "seller"},
    },
    {
        "question": "Những nhóm sản phẩm nào không được đổi trả theo nhu cầu?",
        "gold": "Ví dụ đồ lót/đồ bơi, nước hoa, trang sức, thực phẩm tươi sống và voucher-dịch vụ.",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "Quy trình Nhà Bán xử lý khi nhận lại hàng trả từ khách hàng gồm những bước nào?",
        "gold": "Đồng kiểm và quay clip mở hàng; giữ hàng/clip rồi khiếu nại tại Seller Center nếu có lỗi.",
        "metadata_filter": {"audience": "seller"},
    },
]


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Return simple YAML frontmatter and Markdown body without a YAML dependency."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, flags=re.DOTALL)
    if not match:
        return {}, raw

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        # Corpus values are scalar.  Strip an optional comment and quotes.
        value = value.split("#", 1)[0].strip().strip('"\'')
        metadata[key.strip()] = value
    return metadata, match.group(2)


def load_chunked_documents(corpus_dir: Path = CORPUS_DIR) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(corpus_dir.glob("*.md")):
        metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        doc_id = path.stem
        for index, chunk in enumerate(CHUNKER.chunk(body)):
            documents.append(
                Document(
                    id=f"{doc_id}#{index}",
                    content=chunk,
                    metadata={**metadata, "doc_id": doc_id, "source": str(path)},
                )
            )
    return documents


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    documents = load_chunked_documents()
    if not documents:
        print(f"No Markdown documents found in {CORPUS_DIR}")
        return 1

    store = EmbeddingStore(collection_name="tiki-policy-benchmark", embedding_fn=_mock_embed)
    store.add_documents(documents)
    print(f"Chunker: {CHUNKER.__class__.__name__}; loaded {store.get_collection_size()} chunks from {CORPUS_DIR}")

    for number, benchmark in enumerate(BENCHMARKS, start=1):
        results = store.search_with_filter(
            benchmark["question"], top_k=3, metadata_filter=benchmark["metadata_filter"]
        )
        print(f"\n[{number}] {benchmark['question']}")
        print(f"    Filter: {benchmark['metadata_filter']} | Gold: {benchmark['gold']}")
        for rank, result in enumerate(results, start=1):
            preview = " ".join(result["content"].split())[:180]
            print(f"    {rank}. score={result['score']:.3f} doc_id={result['metadata']['doc_id']} :: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
