"""Tests for omniparser.batch — end-to-end with pypdf fallback."""

import json
from pathlib import Path

from pypdf import PdfWriter

from omniparser.batch import BatchProcessor
from omniparser.config import Settings


def _create_pdf(path: Path, text: str = "") -> Path:
    """Create a minimal PDF file with optional text annotation."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    if text:
        page = writer.pages[0]
        page.merge_page(page)
    with open(path, "wb") as f:
        writer.write(f)
    return path


class TestBatchProcessor:
    def test_no_pdfs_returns_empty_report(self, tmp_path):
        settings = Settings(
            input_dir=tmp_path / "in",
            output_dir=tmp_path / "out",
            max_workers=1,
        )
        (tmp_path / "in").mkdir()
        proc = BatchProcessor(settings)
        report = proc.run()
        assert report.total_files == 0

    def test_single_pdf_sequential(self, tmp_path):
        in_dir = tmp_path / "in"
        out_dir = tmp_path / "out"
        in_dir.mkdir()
        out_dir.mkdir()

        _create_pdf(in_dir / "test.pdf")

        settings = Settings(
            input_dir=in_dir,
            output_dir=out_dir,
            max_workers=1,
        )
        proc = BatchProcessor(settings)
        report = proc.run()

        assert report.total_files == 1
        assert (out_dir / "test.json").exists()

        meta = json.loads((out_dir / "test.json").read_text())
        assert "engine" in meta
        assert "page_count" in meta

    def test_report_json_written(self, tmp_path):
        in_dir = tmp_path / "in"
        out_dir = tmp_path / "out"
        in_dir.mkdir()
        out_dir.mkdir()

        _create_pdf(in_dir / "a.pdf")
        _create_pdf(in_dir / "b.pdf")

        settings = Settings(
            input_dir=in_dir,
            output_dir=out_dir,
            max_workers=1,
        )
        proc = BatchProcessor(settings)
        proc.run()

        report_path = out_dir / "_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["total_files"] == 2
