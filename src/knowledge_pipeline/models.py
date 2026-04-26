from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedArtifact:
    source_path: str
    title: str
    markdown: str
    plain_text: str
    checksum: str
    parser_used: str
    low_confidence: bool = False
    chart_blocks: list[str] = field(default_factory=list)


@dataclass
class EnrichedNote:
    note_id: str
    title: str
    source_path: str
    parser_used: str
    summary: str
    tags: list[str]
    entities: list[str]
    key_points: list[str]
    related_topics: list[str]
    markdown_body: str
    chart_insights: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

