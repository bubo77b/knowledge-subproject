from pathlib import Path

from src.app.settings import AppSettings
from src.pipeline.document_pipeline import DocumentPipeline


def test_pipeline_end_to_end(tmp_path: Path) -> None:
    doc_path = tmp_path / "sample.txt"
    doc_path.write_text("# Topic\nThis is a test document for retrieval.", encoding="utf-8")

    settings = AppSettings(
        output_dir=tmp_path / "md",
        assets_dir=tmp_path / "assets",
        chroma_path=tmp_path / "chroma",
        obsidian_vault_path=tmp_path / "vault",
        mineru_enabled=False,
        chunk_size=80,
        chunk_overlap=10,
    )

    pipeline = DocumentPipeline(settings)
    result = pipeline.ingest(doc_path, to_markdown=True, to_chroma=True, to_obsidian=True)
    assert result.markdown_path.exists()
    assert result.chunk_count >= 1
    assert result.obsidian_note_path is not None
    context = pipeline.retrieve_context("test retrieval", top_k=3)
    assert "doc=" in context or context == ""
