"""OmniParser CLI — industrial-grade PDF-to-Markdown batch processor."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from omniparser import __version__

app = typer.Typer(
    name="omniparser",
    help="Industrial-grade PDF → Markdown batch processor with multi-engine routing.",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    input_dir: Path = typer.Argument(
        ..., help="Directory containing PDF files to process.", exists=True,
    ),
    output_dir: Path = typer.Option(
        "./output", "--output", "-o", help="Directory for Markdown + JSON output.",
    ),
    workers: int = typer.Option(
        1, "--workers", "-w", help="Number of parallel worker processes.",
    ),
    llm: bool = typer.Option(
        False, "--llm", help="Enable LLM-based post-processing.",
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Logging level.",
    ),
) -> None:
    """Batch-convert PDFs in INPUT_DIR to clean Markdown."""
    from omniparser.config import Settings
    from omniparser.logger import setup_logging

    settings = Settings(
        input_dir=input_dir,
        output_dir=output_dir,
        max_workers=workers,
        llm_enabled=llm,
        log_level=log_level,
    )
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    from omniparser.batch import BatchProcessor

    processor = BatchProcessor(settings)
    report = processor.run(input_dir)

    table = Table(title="OmniParser Batch Report")
    table.add_column("File", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Category", style="green")
    table.add_column("Pages", justify="right")
    table.add_column("Tables", justify="right")
    table.add_column("Formulas", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Status", style="bold")

    for r in report.results:
        status = "[green]OK[/green]" if r.success else f"[red]FAIL: {r.error}[/red]"
        table.add_row(
            r.source_path.name,
            r.engine.value,
            r.category.value,
            str(r.page_count),
            str(r.table_count),
            str(r.formula_count),
            f"{r.elapsed_sec:.1f}",
            status,
        )

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {report.total_files} files, "
        f"{report.success_count} succeeded, {report.fail_count} failed, "
        f"{report.total_elapsed_sec:.1f}s elapsed",
    )


@app.command()
def single(
    pdf_path: Path = typer.Argument(
        ..., help="Path to a single PDF file.", exists=True,
    ),
    output_dir: Path = typer.Option(
        "./output", "--output", "-o", help="Output directory.",
    ),
    engine: str = typer.Option(
        "auto", "--engine", "-e",
        help="Force engine: auto, docling, mineru, marker.",
    ),
    llm: bool = typer.Option(
        False, "--llm", help="Enable LLM-based post-processing.",
    ),
) -> None:
    """Process a single PDF file."""
    from omniparser.config import Settings
    from omniparser.logger import setup_logging
    from omniparser.models import EngineType
    from omniparser.parser_engine import get_engine, get_fallback_engine
    from omniparser.postprocessor import LLMPostProcessor, MarkdownPostProcessor
    from omniparser.router import Router

    settings = Settings(output_dir=output_dir, llm_enabled=llm)
    setup_logging(level=settings.log_level, log_file=settings.log_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    if engine == "auto":
        router = Router()
        category, engine_type = router.classify(pdf_path)
    else:
        engine_type = EngineType(engine)

    eng = get_engine(engine_type)
    result = eng.parse(pdf_path)

    if not result.success:
        console.print("[yellow]Primary engine failed, trying pypdf fallback...[/yellow]")
        eng = get_fallback_engine()
        result = eng.parse(pdf_path)

    if result.success:
        postproc = MarkdownPostProcessor()
        result.markdown = postproc.process(result.markdown)

        llm_postproc = LLMPostProcessor(settings)
        result.markdown = llm_postproc.process(result.markdown)

        import json
        md_path = output_dir / f"{pdf_path.stem}.md"
        md_path.write_text(result.markdown, encoding="utf-8")

        meta = {
            "source": str(pdf_path),
            "engine": result.engine.value,
            "category": result.category.value,
            "page_count": result.page_count,
            "table_count": result.table_count,
            "formula_count": result.formula_count,
            "elapsed_sec": round(result.elapsed_sec, 2),
            "elements": [e.to_dict() for e in result.elements],
        }
        meta_path = output_dir / f"{pdf_path.stem}.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        console.print(f"[green]✓[/green] {pdf_path.name} → {md_path}")
        console.print(
            f"  engine={result.engine.value} pages={result.page_count} "
            f"tables={result.table_count} formulas={result.formula_count} "
            f"time={result.elapsed_sec:.1f}s",
        )
    else:
        console.print(f"[red]✗[/red] {pdf_path.name}: {result.error}")


@app.command()
def version() -> None:
    """Print version and exit."""
    console.print(f"OmniParser v{__version__}")


if __name__ == "__main__":
    app()
