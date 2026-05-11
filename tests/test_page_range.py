"""Tests for page range parsing and engine integration."""

from pathlib import Path

import pytest
from pypdf import PdfWriter

from omniparser.models import PageRange, parse_page_range
from omniparser.parser_engine import PyPDFEngine

# ---------------------------------------------------------------------------
# PageRange dataclass
# ---------------------------------------------------------------------------

class TestPageRange:
    def test_basic(self):
        pr = PageRange(1, 50)
        assert pr.start == 1
        assert pr.end == 50
        assert pr.page_count == 50

    def test_single_page(self):
        pr = PageRange(10, 10)
        assert pr.page_count == 1

    def test_str(self):
        assert str(PageRange(1, 100)) == "1-100"

    def test_contains(self):
        pr = PageRange(10, 20)
        assert pr.contains(10)
        assert pr.contains(15)
        assert pr.contains(20)
        assert not pr.contains(9)
        assert not pr.contains(21)

    def test_to_0based_slice(self):
        pr = PageRange(1, 3)
        s = pr.to_0based_slice()
        assert s == slice(0, 3)

    def test_to_0based_slice_offset(self):
        pr = PageRange(5, 10)
        s = pr.to_0based_slice()
        assert s == slice(4, 10)

    def test_start_must_be_positive(self):
        with pytest.raises(ValueError, match="start must be >= 1"):
            PageRange(0, 10)

    def test_end_must_be_gte_start(self):
        with pytest.raises(ValueError, match="end.*must be >= start"):
            PageRange(10, 5)

    def test_frozen(self):
        pr = PageRange(1, 10)
        with pytest.raises(AttributeError):
            pr.start = 2


# ---------------------------------------------------------------------------
# parse_page_range()
# ---------------------------------------------------------------------------

class TestParsePageRange:
    def test_range(self):
        pr = parse_page_range("10-50")
        assert pr == PageRange(10, 50)

    def test_single(self):
        pr = parse_page_range("42")
        assert pr == PageRange(42, 42)

    def test_open_end(self):
        pr = parse_page_range("100-")
        assert pr.start == 100
        assert pr.end == 999_999_999

    def test_open_start(self):
        pr = parse_page_range("-50")
        assert pr == PageRange(1, 50)

    def test_whitespace(self):
        pr = parse_page_range("  10 - 20  ")
        assert pr == PageRange(10, 20)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty page range"):
            parse_page_range("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid page range"):
            parse_page_range("abc")

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError, match="end.*must be >= start"):
            parse_page_range("50-10")


# ---------------------------------------------------------------------------
# PyPDFEngine with page_range
# ---------------------------------------------------------------------------

def _create_multipage_pdf(path: Path, num_pages: int = 5) -> Path:
    """Create a PDF with *num_pages* blank pages."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


class TestPyPDFEnginePageRange:
    def test_no_range_returns_all_pages(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "five.pdf", 5)
        engine = PyPDFEngine()
        result = engine.parse(pdf)
        assert result.page_count == 5
        assert result.page_range is None

    def test_range_first_two(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "five.pdf", 5)
        engine = PyPDFEngine()
        result = engine.parse(pdf, page_range=PageRange(1, 2))
        assert result.page_count == 2
        assert result.page_range == PageRange(1, 2)

    def test_range_middle(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "ten.pdf", 10)
        engine = PyPDFEngine()
        result = engine.parse(pdf, page_range=PageRange(3, 7))
        assert result.page_count == 5
        assert result.page_range == PageRange(3, 7)

    def test_range_beyond_end_clamps(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "three.pdf", 3)
        engine = PyPDFEngine()
        result = engine.parse(pdf, page_range=PageRange(2, 100))
        assert result.page_count == 2

    def test_range_single_page(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "five.pdf", 5)
        engine = PyPDFEngine()
        result = engine.parse(pdf, page_range=PageRange(3, 3))
        assert result.page_count == 1

    def test_page_range_stored_in_result(self, tmp_path):
        pdf = _create_multipage_pdf(tmp_path / "five.pdf", 5)
        engine = PyPDFEngine()
        pr = PageRange(2, 4)
        result = engine.parse(pdf, page_range=pr)
        assert result.page_range is pr
