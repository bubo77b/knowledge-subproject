from __future__ import annotations

from pathlib import Path

import typer

from src.app.settings import load_settings
from src.metrics.quality import evaluate_markdown_quality
from src.pipeline.document_pipeline import DocumentPipeline

app = typer.Typer(help="MinerU Knowledge Skill CLI")


@app.command()
def ingest(
    source: str = typer.Argument(..., help="Document file path or directory path"),
    to_markdown: bool = typer.Option(True, help="Write normalized markdown output"),
    to_chroma: bool = typer.Option(False, help="Ingest chunks into ChromaDB"),
    to_obsidian: bool = typer.Option(False, help="Sync notes into Obsidian vault"),
) -> None:
    settings = load_settings()
    pipeline = DocumentPipeline(settings)
    source_path = Path(source)
    files = [source_path] if source_path.is_file() else [p for p in source_path.rglob("*") if p.is_file()]
    supported = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    files = [p for p in files if p.suffix.lower() in supported]
    if not files:
        typer.echo("No supported files found.")
        raise typer.Exit(1)
    for f in files:
        result = pipeline.ingest(f, to_markdown=to_markdown, to_chroma=to_chroma, to_obsidian=to_obsidian)
        typer.echo(
            f"ingested={f} markdown={result.markdown_path} chunks={result.chunk_count} obsidian={result.obsidian_note_path}"
        )


@app.command()
def search(query: str, top_k: int = 6) -> None:
    settings = load_settings()
    pipeline = DocumentPipeline(settings)
    hits = pipeline.search(query, top_k=top_k)
    if not hits:
        typer.echo("No results.")
        return
    for idx, hit in enumerate(hits, start=1):
        preview = hit.text.replace("\n", " ")[:180]
        typer.echo(f"{idx}. score={hit.score:.3f} doc={hit.doc_id} chunk={hit.chunk_id} text={preview}")


@app.command()
def context(query: str, top_k: int = 6, max_chars: int = 4000) -> None:
    settings = load_settings()
    pipeline = DocumentPipeline(settings)
    text = pipeline.retrieve_context(query, top_k=top_k, max_chars=max_chars)
    typer.echo(text if text else "No context returned.")


@app.command()
def evaluate(source: str = typer.Argument(..., help="Single source document path")) -> None:
    settings = load_settings()
    pipeline = DocumentPipeline(settings)
    result = pipeline.ingest(source, to_markdown=True, to_chroma=False, to_obsidian=False)
    quality = evaluate_markdown_quality(result.document.markdown, result.document.plain_text)
    typer.echo(f"structure_integrity={quality.structure_integrity}")
    typer.echo(f"table_fidelity={quality.table_fidelity}")
    typer.echo(f"paragraph_preservation={quality.paragraph_preservation}")


if __name__ == "__main__":
    app()
