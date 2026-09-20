from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "No relevant documents were found in the knowledge base."

        context_parts = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source") or metadata.get("doc_id") or result.get("id", "unknown")
            context_parts.append(f"[{index}] Source: {source}\n{result['content']}")

        prompt = (
            "Answer the question using only the context below. "
            "If the context does not contain the answer, say that you could not find it. "
            "Cite the supporting context chunk number(s), for example [1].\n\n"
            f"Context:\n{'\n\n'.join(context_parts)}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return self.llm_fn(prompt)
