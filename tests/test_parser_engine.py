"""Tests for omniparser.parser_engine."""

from pathlib import Path

import pytest

from omniparser.models import EngineType
from omniparser.parser_engine import (
    BaseEngine,
    PyPDFEngine,
    get_engine,
    get_fallback_engine,
)


class TestBaseEngineHelpers:
    def test_count_tables(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n\ntext\n\n| x | y |\n|---|---|\n| 3 | 4 |"
        assert BaseEngine._count_tables(md) == 2

    def test_count_formulas_inline(self):
        md = "The value $x$ and $y$ are important."
        assert BaseEngine._count_formulas(md) == 2

    def test_count_formulas_block(self):
        md = "$$E = mc^2$$\n\n$$F = ma$$"
        assert BaseEngine._count_formulas(md) == 2

    def test_count_formulas_mixed(self):
        md = "Inline $x$ and block:\n$$y = f(x)$$"
        assert BaseEngine._count_formulas(md) == 2


class TestPyPDFEngine:
    def test_parse_nonexistent_file(self):
        engine = PyPDFEngine()
        result = engine.parse(Path("/nonexistent/test.pdf"))
        assert not result.success
        assert result.error is not None

    def test_parse_produces_result_structure(self, tmp_path):
        """Create a minimal valid PDF and parse it with pypdf."""
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf_path = tmp_path / "blank.pdf"
        with open(pdf_path, "wb") as f:
            writer.write(f)

        engine = PyPDFEngine()
        result = engine.parse(pdf_path)
        assert result.page_count == 1
        assert result.source_path == pdf_path
        assert result.elapsed_sec > 0


class TestGetEngine:
    def test_docling_engine_type(self):
        engine = get_engine(EngineType.DOCLING)
        assert engine.engine_type == EngineType.DOCLING

    def test_mineru_engine_type(self):
        engine = get_engine(EngineType.MINERU)
        assert engine.engine_type == EngineType.MINERU

    def test_marker_engine_type(self):
        engine = get_engine(EngineType.MARKER)
        assert engine.engine_type == EngineType.MARKER

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("nonexistent")

    def test_fallback_engine(self):
        engine = get_fallback_engine()
        assert isinstance(engine, PyPDFEngine)
