from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class AppConfig:
    input_dir: Path
    obsidian_vault_dir: Path
    notes_subdir: str
    sqlite_path: Path
    parser_order: list[str]
    parser_timeout_seconds: int
    fallback_parser_enabled: bool
    chart_extractor: str
    chart_min_chars: int
    large_pdf_page_threshold: int
    pdf_batch_pages: int
    llm_provider: str
    llm_enabled: bool
    llm_model: str
    llm_api_key: str | None
    llm_base_url: str | None
    max_chars_for_analysis: int
    ai_chunk_size_chars: int
    ai_chunk_overlap_chars: int
    ai_max_chunks: int


def load_config() -> AppConfig:
    load_dotenv()

    input_dir = Path(os.getenv("INPUT_DIR", "./input_docs")).resolve()
    obsidian_vault_dir = Path(os.getenv("OBSIDIAN_VAULT_DIR", "./obsidian_vault")).resolve()
    notes_subdir = os.getenv("OBSIDIAN_NOTES_SUBDIR", "AI-Knowledge")
    sqlite_path = Path(os.getenv("SQLITE_PATH", "./knowledge.db")).resolve()
    parser_order_raw = os.getenv("PARSER_ORDER", "mineru,paddleocr")
    parser_order = [item.strip().lower() for item in parser_order_raw.split(",") if item.strip()]
    parser_timeout_seconds = int(os.getenv("PARSER_TIMEOUT_SECONDS", "120"))
    fallback_parser_enabled = os.getenv("FALLBACK_PARSER_ENABLED", "true").lower() == "true"
    chart_extractor = os.getenv("CHART_EXTRACTOR", "none").lower()
    chart_min_chars = int(os.getenv("CHART_MIN_CHARS", "80"))
    large_pdf_page_threshold = int(os.getenv("LARGE_PDF_PAGE_THRESHOLD", "300"))
    pdf_batch_pages = int(os.getenv("PDF_BATCH_PAGES", "50"))
    llm_provider = os.getenv("LLM_PROVIDER", "none").lower()
    llm_enabled = os.getenv("LLM_ENABLED", "false").lower() == "true"
    llm_model = os.getenv("LLM_MODEL", "qwen2.5:7b")
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL")
    max_chars_for_analysis = int(os.getenv("MAX_CHARS_FOR_ANALYSIS", "8000"))
    ai_chunk_size_chars = int(os.getenv("AI_CHUNK_SIZE_CHARS", "6000"))
    ai_chunk_overlap_chars = int(os.getenv("AI_CHUNK_OVERLAP_CHARS", "600"))
    ai_max_chunks = int(os.getenv("AI_MAX_CHUNKS", "120"))

    if llm_provider not in {"none", "openai", "ollama"}:
        llm_provider = "none"
    if llm_provider == "ollama" and not llm_base_url:
        llm_base_url = "http://localhost:11434/v1"
    if llm_provider == "ollama" and not llm_api_key:
        llm_api_key = "ollama"

    return AppConfig(
        input_dir=input_dir,
        obsidian_vault_dir=obsidian_vault_dir,
        notes_subdir=notes_subdir,
        sqlite_path=sqlite_path,
        parser_order=parser_order,
        parser_timeout_seconds=parser_timeout_seconds,
        fallback_parser_enabled=fallback_parser_enabled,
        chart_extractor=chart_extractor,
        chart_min_chars=chart_min_chars,
        large_pdf_page_threshold=large_pdf_page_threshold,
        pdf_batch_pages=pdf_batch_pages,
        llm_provider=llm_provider,
        llm_enabled=llm_enabled,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        max_chars_for_analysis=max_chars_for_analysis,
        ai_chunk_size_chars=ai_chunk_size_chars,
        ai_chunk_overlap_chars=ai_chunk_overlap_chars,
        ai_max_chunks=ai_max_chunks,
    )

