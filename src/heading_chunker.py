"""A chunker for Markdown policies and FAQs whose headings define topics."""

from __future__ import annotations

import re

from .chunking import RecursiveChunker


class HeadingChunker:
    """Keep each Markdown heading and its section together when possible."""

    HEADING_RE = re.compile(r"(?m)^(#{1,6}\s+.+)$")

    def __init__(self, chunk_size: int = 500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        matches = list(self.HEADING_RE.finditer(text))
        if not matches:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        chunks: list[str] = []
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chunks.extend(RecursiveChunker(chunk_size=self.chunk_size).chunk(preamble))

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = text[match.start() : end].strip()
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            heading = match.group(1).strip()
            body = section[len(match.group(0)) :].strip()
            # Reserve room for the heading, then prepend it to every fallback
            # piece so a retrieved continuation remains self-describing.
            body_size = max(1, self.chunk_size - len(heading) - 1)
            pieces = RecursiveChunker(chunk_size=body_size).chunk(body)
            chunks.extend(f"{heading}\n{piece}" for piece in pieces if piece.strip())
        return chunks
