from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    doc_id: str
    source_path: Path
    source_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, str] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    metadata: DocumentMetadata
    markdown: str
    plain_text: str
    assets: list[Path] = Field(default_factory=list)


class TextChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    section: str = ""
    order: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: dict[str, str] = Field(default_factory=dict)


class ObsidianNote(BaseModel):
    note_path: Path
    title: str
    content: str
    backlinks_updated: list[Path] = Field(default_factory=list)
