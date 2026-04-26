from __future__ import annotations

import hashlib
import re
import sys
import time
from pathlib import Path

from .analyzer import build_knowledge_note
from .config import AppConfig
from .document_parser import SUPPORTED_EXTENSIONS, parse_document
from .obsidian_writer import ObsidianWriter
from .storage import Storage


def run_pipeline(config: AppConfig) -> dict[str, int]:
    started_at = time.perf_counter()
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.obsidian_vault_dir.mkdir(parents=True, exist_ok=True)

    storage = Storage(config.sqlite_path)
    writer = ObsidianWriter(config.obsidian_vault_dir, config.notes_subdir)
    stats = {"processed": 0, "skipped": 0, "failed": 0}
    files = list(_iter_input_files(config.input_dir))
    _log(f"Found {len(files)} supported files in {config.input_dir}")

    try:
        for index, file_path in enumerate(files, start=1):
            file_started = time.perf_counter()
            _log(f"[{index}/{len(files)}] Processing {file_path.name}")
            try:
                doc = parse_document(file_path, config)
                if storage.is_document_seen(doc):
                    stats["skipped"] += 1
                    _log(f"[{index}/{len(files)}] Skipped (unchanged checksum)")
                    continue

                note_id = _build_note_id(doc.title, doc.source_path)
                note = build_knowledge_note(doc, config, note_id=note_id)
                related_ids = _find_related_ids(note.related_topics, storage.list_notes())
                title_map = storage.get_note_title_map()
                note_path = writer.write_note(note, related_ids, title_map)

                for related_id in related_ids:
                    related_title = title_map.get(related_id, related_id)
                    writer.ensure_backlink(related_id, note.note_id, note.title)
                    writer.ensure_backlink(note.note_id, related_id, related_title)
                    storage.record_link(note.note_id, related_id)
                    storage.record_link(related_id, note.note_id)

                storage.upsert_document(doc)
                storage.upsert_note(note, str(note_path))
                stats["processed"] += 1
                elapsed = time.perf_counter() - file_started
                _log(
                    f"[{index}/{len(files)}] Done parser={doc.parser_used} "
                    f"related={len(related_ids)} elapsed={elapsed:.1f}s"
                )
            except Exception as exc:
                stats["failed"] += 1
                _log(f"[{index}/{len(files)}] Failed: {file_path.name} ({exc})")
    finally:
        storage.close()

    total_elapsed = time.perf_counter() - started_at
    _log(
        f"Pipeline finished processed={stats['processed']} skipped={stats['skipped']} "
        f"failed={stats['failed']} elapsed={total_elapsed:.1f}s"
    )
    return stats


def _iter_input_files(input_dir: Path):
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def _build_note_id(title: str, source_path: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", title.lower()).strip("-")
    if not base:
        base = "note"
    digest = hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def _find_related_ids(related_topics: list[str], notes: list[tuple[str, str, str]]) -> list[str]:
    if not related_topics:
        return []
    topics = [item.lower().strip() for item in related_topics if item.strip()]
    if not topics:
        return []

    matches: list[str] = []
    for note_id, title, summary in notes:
        combined = f"{title} {summary}".lower()
        score = sum(1 for topic in topics if topic and topic in combined)
        if score > 0:
            matches.append((note_id, score))

    matches.sort(key=lambda item: item[1], reverse=True)
    return [note_id for note_id, _ in matches[:5]]


def _log(message: str) -> None:
    text = f"[knowledge-pipeline] {message}"
    safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
    print(safe, flush=True)

