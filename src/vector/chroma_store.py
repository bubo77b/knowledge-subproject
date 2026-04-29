from __future__ import annotations

import hashlib
import math
from pathlib import Path

import chromadb

from src.models.schemas import SearchHit, TextChunk


class ChromaStore:
    def __init__(self, persist_path: Path, collection_name: str):
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert_chunks(self, chunks: list[TextChunk]) -> int:
        if not chunks:
            return 0
        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metadatas = [{**c.metadata, "doc_id": c.doc_id, "chunk_id": c.chunk_id} for c in chunks]
        embeddings = [self._embed(c.text) for c in chunks]
        self.collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
        return len(chunks)

    def search(self, query: str, top_k: int = 6) -> list[SearchHit]:
        q_embed = self._embed(query)
        res = self.collection.query(query_embeddings=[q_embed], n_results=top_k)
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        hits: list[SearchHit] = []
        for chunk_id, text, meta, dist in zip(ids, docs, metadatas, distances):
            score = 1.0 / (1.0 + float(dist))
            hits.append(
                SearchHit(
                    chunk_id=chunk_id,
                    doc_id=(meta or {}).get("doc_id", ""),
                    text=text,
                    metadata=meta or {},
                    score=score,
                )
            )
        return hits

    def retrieve_context(self, query: str, top_k: int = 6, max_chars: int = 4000) -> str:
        hits = self.search(query, top_k=top_k)
        blocks: list[str] = []
        total = 0
        for hit in hits:
            block = f"[doc={hit.doc_id} chunk={hit.chunk_id} score={hit.score:.3f}]\n{hit.text}"
            if total + len(block) > max_chars:
                break
            blocks.append(block)
            total += len(block)
        return "\n\n".join(blocks)

    def _embed(self, text: str, dims: int = 256) -> list[float]:
        # Deterministic lightweight embedding without external model runtime.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for i in range(dims):
            b = digest[i % len(digest)]
            values.append((b / 127.5) - 1.0)
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
