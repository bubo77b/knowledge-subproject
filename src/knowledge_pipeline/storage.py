from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import EnrichedNote, ParsedArtifact


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    checksum TEXT NOT NULL,
    plain_text TEXT NOT NULL,
    parser_used TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    summary TEXT NOT NULL,
    markdown_path TEXT NOT NULL,
    parser_used TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT NOT NULL,
    linked_note_id TEXT NOT NULL,
    UNIQUE(note_id, linked_note_id)
);
"""


class Storage:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.sqlite_path))
        self.conn.executescript(SCHEMA)
        self._run_migrations()
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _run_migrations(self) -> None:
        self._ensure_column("documents", "plain_text", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("documents", "parser_used", "TEXT NOT NULL DEFAULT 'unknown'")
        self._ensure_column("notes", "parser_used", "TEXT NOT NULL DEFAULT 'unknown'")

    def _ensure_column(self, table_name: str, column_name: str, definition: str) -> None:
        rows = self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {row[1] for row in rows}
        if column_name not in existing:
            self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def is_document_seen(self, document: ParsedArtifact) -> bool:
        row = self.conn.execute(
            "SELECT checksum FROM documents WHERE source_path = ?",
            (document.source_path,),
        ).fetchone()
        return bool(row and row[0] == document.checksum)

    def upsert_document(self, document: ParsedArtifact) -> None:
        self.conn.execute(
            """
            INSERT INTO documents (source_path, title, checksum, plain_text, parser_used)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_path)
            DO UPDATE SET
                title=excluded.title,
                checksum=excluded.checksum,
                plain_text=excluded.plain_text,
                parser_used=excluded.parser_used
            """,
            (document.source_path, document.title, document.checksum, document.plain_text, document.parser_used),
        )
        self.conn.commit()

    def upsert_note(self, note: EnrichedNote, markdown_path: str) -> None:
        self.conn.execute(
            """
            INSERT INTO notes (note_id, title, source_path, summary, markdown_path, parser_used)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(note_id)
            DO UPDATE SET
                title=excluded.title,
                source_path=excluded.source_path,
                summary=excluded.summary,
                markdown_path=excluded.markdown_path,
                parser_used=excluded.parser_used
            """,
            (note.note_id, note.title, note.source_path, note.summary, markdown_path, note.parser_used),
        )
        self.conn.commit()

    def record_link(self, note_id: str, linked_note_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO links (note_id, linked_note_id)
            VALUES (?, ?)
            """,
            (note_id, linked_note_id),
        )
        self.conn.commit()

    def get_note_title_map(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT note_id, title FROM notes").fetchall()
        return {row[0]: row[1] for row in rows}

    def list_notes(self) -> list[tuple[str, str, str]]:
        rows = self.conn.execute("SELECT note_id, title, summary FROM notes").fetchall()
        return [(row[0], row[1], row[2]) for row in rows]

