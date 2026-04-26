from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document
from markdownify import markdownify as html_to_markdown
from pypdf import PdfReader

from .config import AppConfig
from .models import ParsedArtifact


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".html", ".htm"}


def parse_document(path: Path, config: AppConfig) -> ParsedArtifact:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")
    _log(f"Parsing file={path.name} type={suffix}")

    if suffix in {".pdf"}:
        parsed = _parse_pdf_with_pipeline(path, config)
        markdown = parsed["markdown"]
        raw_text = parsed["plain_text"]
        parser_used = parsed["parser_used"]
        low_confidence = parsed["low_confidence"]
    elif suffix == ".docx":
        raw_text = _parse_docx(path)
        markdown = _as_markdown_paragraphs(raw_text)
        parser_used = "python-docx"
        low_confidence = False
    elif suffix == ".md":
        markdown = path.read_text(encoding="utf-8", errors="ignore")
        raw_text = markdown
        parser_used = "native-markdown"
        low_confidence = False
    elif suffix == ".txt":
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        markdown = raw_text
        parser_used = "native-text"
        low_confidence = False
    else:
        raw_text, markdown = _parse_html(path)
        parser_used = "beautifulsoup-markdownify"
        low_confidence = False

    checksum = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()
    title = _resolve_title(path, raw_text)
    return ParsedArtifact(
        source_path=str(path.resolve()),
        title=title,
        plain_text=raw_text.strip(),
        markdown=markdown.strip(),
        checksum=checksum,
        parser_used=parser_used,
        low_confidence=low_confidence,
    )


def _parse_pdf_with_pipeline(path: Path, config: AppConfig) -> dict[str, str | bool]:
    page_count = _safe_pdf_page_count(path)
    _log(f"PDF pages detected: {page_count} for {path.name}")
    if page_count >= config.large_pdf_page_threshold and config.fallback_parser_enabled:
        _log(
            f"Large PDF shortcut enabled ({page_count} >= {config.large_pdf_page_threshold}), "
            f"using pagewise pypdf batch={config.pdf_batch_pages}"
        )
        raw_text = _parse_pdf_pagewise(path, config.pdf_batch_pages)
        return {
            "markdown": _as_markdown_paragraphs(raw_text),
            "plain_text": raw_text,
            "parser_used": "pypdf-pagewise-largefile",
            "low_confidence": True,
        }

    for parser_name in config.parser_order:
        if parser_name == "mineru":
            _log("Trying parser: mineru")
            result = _run_mineru(path, config)
            if result:
                _log("Parser success: mineru")
                return {**result, "parser_used": "mineru", "low_confidence": False}
        elif parser_name == "paddleocr":
            _log("Trying parser: paddleocr")
            result = _run_command_parser(["paddleocr", "--image_dir", str(path)], config)
            if result:
                _log("Parser success: paddleocr")
                return {**result, "parser_used": "paddleocr", "low_confidence": True}

    if config.fallback_parser_enabled:
        _log("All configured parsers failed, fallback to pypdf pagewise")
        raw_text = _parse_pdf_pagewise(path, config.pdf_batch_pages)
        return {
            "markdown": _as_markdown_paragraphs(raw_text),
            "plain_text": raw_text,
            "parser_used": "pypdf-fallback",
            "low_confidence": True,
        }
    raise RuntimeError(f"No parser succeeded for: {path}")


def _safe_pdf_page_count(path: Path) -> int:
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0


def _parse_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_pdf_pagewise(path: Path, batch_pages: int) -> str:
    reader = PdfReader(str(path))
    batches: list[str] = []
    page_count = len(reader.pages)
    _log(f"Pagewise extraction start pages={page_count} batch_size={batch_pages}")
    for start in range(0, page_count, batch_pages):
        stop = min(start + batch_pages, page_count)
        _log(f"Extracting pages {start + 1}-{stop}")
        batch_text = []
        for page_idx in range(start, stop):
            batch_text.append(reader.pages[page_idx].extract_text() or "")
        batches.append("\n\n".join(batch_text))
    return "\n\n".join(batches)


def _run_mineru(path: Path, config: AppConfig) -> dict[str, str] | None:
    with tempfile.TemporaryDirectory(prefix="mineru_out_") as output_dir:
        command = ["mineru", "-p", str(path), "-o", output_dir]
        _log(f"Running command: {' '.join(command)}")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=config.parser_timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            _log(f"MinerU failed code={completed.returncode}")
            return None

        output_path = Path(output_dir)
        md_files = sorted(output_path.rglob("*.md"))
        if not md_files:
            return None

        markdown_parts = [md.read_text(encoding="utf-8", errors="ignore") for md in md_files]
        markdown = "\n\n".join(part.strip() for part in markdown_parts if part.strip())
        if not markdown:
            _log("MinerU produced empty markdown")
            return None
        plain_text = _strip_markdown(markdown)
        return {"markdown": markdown, "plain_text": plain_text}


def _run_command_parser(command: list[str], config: AppConfig) -> dict[str, str] | None:
    try:
        _log(f"Running command: {' '.join(command)}")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=config.parser_timeout_seconds,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            _log(f"Command parser failed code={completed.returncode}")
            return None
        markdown = completed.stdout.strip()
        plain_text = _strip_markdown(markdown)
        return {"markdown": markdown, "plain_text": plain_text}
    except (subprocess.SubprocessError, OSError):
        return None


def _parse_docx(path: Path) -> str:
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(parts)


def _parse_html(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(content, "html.parser")
    raw_text = soup.get_text(separator="\n")
    markdown = html_to_markdown(content)
    return raw_text, markdown


def _as_markdown_paragraphs(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    blocks = [line for line in lines if line]
    return "\n\n".join(blocks)


def _resolve_title(path: Path, text: str) -> str:
    candidate = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if candidate:
        return candidate[:80]
    return path.stem


def _strip_markdown(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
    text = re.sub(r"[#>*`~\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _log(message: str) -> None:
    text = f"[parser] {message}"
    safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
    print(safe, flush=True)

