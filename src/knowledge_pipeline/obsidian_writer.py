from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import EnrichedNote


BACKLINK_SECTION = "## Backlinks"


class ObsidianWriter:
    def __init__(self, vault_dir: Path, notes_subdir: str) -> None:
        self.notes_root = vault_dir / notes_subdir
        self.notes_root.mkdir(parents=True, exist_ok=True)

    def note_path(self, note_id: str) -> Path:
        return self.notes_root / f"{note_id}.md"

    def write_note(self, note: EnrichedNote, related_note_ids: Iterable[str], title_map: dict[str, str]) -> Path:
        path = self.note_path(note.note_id)
        related_links = [self._wikilink(note_id, title_map.get(note_id, note_id)) for note_id in related_note_ids]
        content = self._build_note_content(note, related_links)
        path.write_text(content, encoding="utf-8")
        return path

    def ensure_backlink(self, target_note_id: str, source_note_id: str, source_title: str) -> None:
        path = self.note_path(target_note_id)
        if not path.exists():
            return
        backlink = self._wikilink(source_note_id, source_title)
        content = path.read_text(encoding="utf-8", errors="ignore")
        if backlink in content:
            return
        if BACKLINK_SECTION in content:
            updated = content + f"\n- {backlink}\n"
        else:
            updated = content.rstrip() + f"\n\n{BACKLINK_SECTION}\n- {backlink}\n"
        path.write_text(updated, encoding="utf-8")

    def _build_note_content(self, note: EnrichedNote, related_links: list[str]) -> str:
        tags = " ".join(f"#{self._safe_tag(tag)}" for tag in note.tags)
        entities = ", ".join(note.entities) if note.entities else "无"
        key_points_md = "\n".join(f"- {item}" for item in note.key_points) or "- 无"
        related_md = "\n".join(f"- {link}" for link in related_links) or "- 无"
        chart_md = "\n".join(f"- {item}" for item in note.chart_insights) or "- 无"

        return (
            f"---\n"
            f"note_id: {note.note_id}\n"
            f"source_path: {note.source_path}\n"
            f"parser_used: {note.parser_used}\n"
            f"created_at: {note.created_at.isoformat()}Z\n"
            f"---\n\n"
            f"# {note.title}\n\n"
            f"## Summary\n{note.summary}\n\n"
            f"## Tags\n{tags}\n\n"
            f"## Entities\n{entities}\n\n"
            f"## Key Points\n{key_points_md}\n\n"
            f"## Chart Insights\n{chart_md}\n\n"
            f"## Related Notes\n{related_md}\n\n"
            f"## Source Markdown\n{note.markdown_body}\n\n"
            f"{BACKLINK_SECTION}\n"
        )

    @staticmethod
    def _wikilink(note_id: str, title: str) -> str:
        title = title.replace("[", "").replace("]", "")
        return f"[[{note_id}|{title}]]"

    @staticmethod
    def _safe_tag(value: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff\-]", "", value.lower()) or "imported"

