from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from src.app.settings import load_settings
from src.pipeline.document_pipeline import DocumentPipeline

settings = load_settings()
pipeline = DocumentPipeline(settings)
app = FastAPI(title=settings.project_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    to_markdown: bool = Form(True),
    to_chroma: bool = Form(False),
    to_obsidian: bool = Form(False),
) -> dict[str, str | int | None]:
    suffix = Path(file.filename or "upload.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    result = pipeline.ingest(tmp_path, to_markdown=to_markdown, to_chroma=to_chroma, to_obsidian=to_obsidian)
    return {
        "doc_id": result.document.metadata.doc_id,
        "markdown_path": str(result.markdown_path),
        "chunk_count": result.chunk_count,
        "obsidian_note_path": str(result.obsidian_note_path) if result.obsidian_note_path else None,
    }


@app.post("/search")
def search(query: str = Form(...), top_k: int = Form(6)) -> dict[str, list[dict[str, str | float]]]:
    hits = pipeline.search(query, top_k)
    return {
        "results": [
            {
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "text": h.text,
                "score": h.score,
            }
            for h in hits
        ]
    }


@app.post("/retrieve_context")
def retrieve_context(query: str = Form(...), top_k: int = Form(6), max_chars: int = Form(4000)) -> dict[str, str]:
    context = pipeline.retrieve_context(query, top_k=top_k, max_chars=max_chars)
    return {"context": context}
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from src.app.settings import load_settings
from src.pipeline.document_pipeline import DocumentPipeline

settings = load_settings()
pipeline = DocumentPipeline(settings)
app = FastAPI(title=settings.project_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    to_markdown: bool = Form(True),
    to_chroma: bool = Form(False),
    to_obsidian: bool = Form(False),
) -> dict[str, str | int | None]:
    suffix = Path(file.filename or "upload.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    result = pipeline.ingest(tmp_path, to_markdown=to_markdown, to_chroma=to_chroma, to_obsidian=to_obsidian)
    return {
        "doc_id": result.document.metadata.doc_id,
        "markdown_path": str(result.markdown_path),
        "chunk_count": result.chunk_count,
        "obsidian_note_path": str(result.obsidian_note_path) if result.obsidian_note_path else None,
    }


@app.post("/search")
def search(query: str = Form(...), top_k: int = Form(6)) -> dict[str, list[dict[str, str | float]]]:
    hits = pipeline.search(query, top_k)
    return {
        "results": [
            {
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "text": h.text,
                "score": h.score,
            }
            for h in hits
        ]
    }


@app.post("/retrieve_context")
def retrieve_context(query: str = Form(...), top_k: int = Form(6), max_chars: int = Form(4000)) -> dict[str, str]:
    context = pipeline.retrieve_context(query, top_k=top_k, max_chars=max_chars)
    return {"context": context}
