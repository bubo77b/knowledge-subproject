from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.app.settings import AppSettings
from src.markdown.normalizer import MarkdownNormalizer
from src.models.schemas import ParsedDocument, SearchHit, TextChunk
from src.obsidian.linker import ObsidianLinker
from src.obsidian.obsidian_sync import ObsidianSync
from src.parsers.mineru_parser import MinerUParser
from src.vector.chroma_store import ChromaStore
from src.vector.chunker import ChunkerConfig, SemanticChunker


@dataclass
class IngestResult:
    document: ParsedDocument
    markdown_path: Path
    chunk_count: int
    obsidian_note_path: Path | None


class DocumentPipeline:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.parser = MinerUParser(mineru_enabled=settings.mineru_enabled)
        self.normalizer = MarkdownNormalizer()
        self.chunker = SemanticChunker(ChunkerConfig(settings.chunk_size, settings.chunk_overlap))
        self.vector_store = ChromaStore(settings.chroma_path, settings.chroma_collection)
        self.linker = ObsidianLinker(
            synonym_map=settings.synonym_map,
            keyword_min_len=settings.keyword_min_len,
            keyword_top_k=settings.keyword_top_k,
        )
        self.obsidian = ObsidianSync(
            vault_path=settings.obsidian_vault_path,
            managed_block_start=settings.obsidian_managed_block_start,
            managed_block_end=settings.obsidian_managed_block_end,
        )

    def ingest(
        self,
        source_path: str | Path,
        to_markdown: bool = True,
        to_chroma: bool = False,
        to_obsidian: bool = False,
    ) -> IngestResult:
        parsed = self.parser.parse(source_path)
        normalized_md = self.normalizer.normalize(parsed.markdown)
        parsed.markdown = normalized_md
        md_path = self._write_markdown(parsed) if to_markdown else Path("")

        chunks: list[TextChunk] = []
        if to_chroma:
            chunks = self.chunker.chunk(parsed.metadata.doc_id, parsed.markdown)
            self.vector_store.upsert_chunks(chunks)

        obsidian_note_path: Path | None = None
        if to_obsidian:
            keywords = self.linker.extract_keywords(parsed.markdown)
            linked_md, _ = self.linker.inject_wikilinks(parsed.markdown, keywords)
            note = self.obsidian.sync_document(parsed, linked_md, keywords)
            obsidian_note_path = note.note_path

        return IngestResult(
            document=parsed,
            markdown_path=md_path,
            chunk_count=len(chunks),
            obsidian_note_path=obsidian_note_path,
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchHit]:
        return self.vector_store.search(query=query, top_k=top_k or self.settings.context_top_k)

    def retrieve_context(self, query: str, top_k: int | None = None, max_chars: int = 4000) -> str:
        return self.vector_store.retrieve_context(
            query=query,
            top_k=top_k or self.settings.context_top_k,
            max_chars=max_chars,
        )

    def _write_markdown(self, parsed: ParsedDocument) -> Path:
        out_path = self.settings.output_dir / f"{parsed.metadata.source_path.stem}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(parsed.markdown, encoding="utf-8")
        return out_path
