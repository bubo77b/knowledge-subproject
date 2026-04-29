from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.models.schemas import ObsidianNote, ParsedDocument


class ObsidianSync:
    def __init__(self, vault_path: Path, managed_block_start: str, managed_block_end: str):
        self.vault_path = vault_path
        self.managed_block_start = managed_block_start
        self.managed_block_end = managed_block_end
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def sync_document(self, doc: ParsedDocument, linked_markdown: str, keywords: list[str]) -> ObsidianNote:
        title = doc.metadata.source_path.stem
        note_path = self.vault_path / f"{title}.md"
        frontmatter = self._build_frontmatter(doc.metadata.doc_id, str(doc.metadata.source_path), keywords)
        managed = f"{self.managed_block_start}\n{linked_markdown.strip()}\n{self.managed_block_end}\n"
        user_content = self._extract_user_block(note_path)
        content = f"{frontmatter}\n{managed}\n{user_content}".strip() + "\n"
        note_path.write_text(content, encoding="utf-8")
        backlinks_updated = self._append_backlinks(title, keywords)
        return ObsidianNote(note_path=note_path, title=title, content=content, backlinks_updated=backlinks_updated)

    def _build_frontmatter(self, doc_id: str, source: str, keywords: list[str]) -> str:
        tags = ", ".join(keywords[:10])
        now = datetime.now(timezone.utc).isoformat()
        return (
            "---\n"
            f"doc_id: {doc_id}\n"
            f"source: {source}\n"
            f"tags: [{tags}]\n"
            f"updated_at: {now}\n"
            "---"
        )

    def _extract_user_block(self, note_path: Path) -> str:
        if not note_path.exists():
            return "## User Notes\n"
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        if self.managed_block_end not in text:
            return text
        return text.split(self.managed_block_end, 1)[-1].strip() or "## User Notes\n"

    def _append_backlinks(self, title: str, keywords: list[str]) -> list[Path]:
        updated: list[Path] = []
        for kw in keywords:
            path = self.vault_path / f"{kw}.md"
            backlink_line = f"- [[{title}]]\n"
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
            else:
                text = f"# {kw}\n\n## Backlinks\n"
            if backlink_line.strip() in text:
                continue
            if "## Backlinks" not in text:
                text += "\n## Backlinks\n"
            text += backlink_line
            path.write_text(text, encoding="utf-8")
            updated.append(path)
        return updated
