from __future__ import annotations

import argparse
import json

from .config import load_config
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest documents, convert to Markdown, and sync into Obsidian notes."
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved configuration and exit.",
    )
    args = parser.parse_args()

    config = load_config()
    if args.print_config:
        payload = {
            "input_dir": str(config.input_dir),
            "obsidian_vault_dir": str(config.obsidian_vault_dir),
            "notes_subdir": config.notes_subdir,
            "sqlite_path": str(config.sqlite_path),
            "parser_order": config.parser_order,
            "parser_timeout_seconds": config.parser_timeout_seconds,
            "fallback_parser_enabled": config.fallback_parser_enabled,
            "chart_extractor": config.chart_extractor,
            "large_pdf_page_threshold": config.large_pdf_page_threshold,
            "pdf_batch_pages": config.pdf_batch_pages,
            "llm_provider": config.llm_provider,
            "llm_enabled": config.llm_enabled,
            "llm_model": config.llm_model,
            "llm_base_url": config.llm_base_url,
            "max_chars_for_analysis": config.max_chars_for_analysis,
            "ai_chunk_size_chars": config.ai_chunk_size_chars,
            "ai_chunk_overlap_chars": config.ai_chunk_overlap_chars,
            "ai_max_chunks": config.ai_max_chunks,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    stats = run_pipeline(config)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

