from __future__ import annotations

import hashlib
from dataclasses import dataclass

from src.models.schemas import TextChunk


@dataclass
class ChunkerConfig:
    chunk_size: int = 800
    chunk_overlap: int = 120


class SemanticChunker:
    def __init__(self, config: ChunkerConfig):
        self.config = config

    def chunk(self, doc_id: str, markdown: str) -> list[TextChunk]:
        sections = self._split_sections(markdown)
        chunks: list[TextChunk] = []
        order = 0
        for section_title, section_text in sections:
            chunks.extend(self._split_text(doc_id, section_title, section_text, order))
            order = len(chunks)
        return chunks

    def _split_sections(self, markdown: str) -> list[tuple[str, str]]:
        current_title = "root"
        current_lines: list[str] = []
        sections: list[tuple[str, str]] = []
        for line in markdown.splitlines():
            if line.startswith("#"):
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                    current_lines = []
                current_title = line.lstrip("#").strip() or "untitled"
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))
        if not sections:
            sections.append(("root", markdown.strip()))
        return sections

    def _split_text(self, doc_id: str, section: str, text: str, start_order: int) -> list[TextChunk]:
        if not text:
            return []
        size = self.config.chunk_size
        overlap = min(self.config.chunk_overlap, max(0, size // 2))
        chunks: list[TextChunk] = []
        start = 0
        order = start_order
        while start < len(text):
            end = min(len(text), start + size)
            body = text[start:end].strip()
            if body:
                chunk_id = hashlib.sha1(f"{doc_id}:{section}:{order}:{body}".encode("utf-8")).hexdigest()[:20]
                chunks.append(
                    TextChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        section=section,
                        text=body,
                        order=order,
                        metadata={"section": section, "order": str(order)},
                    )
                )
                order += 1
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
        return chunks
