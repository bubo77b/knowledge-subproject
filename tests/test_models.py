"""Tests for omniparser.models."""

from pathlib import Path

from omniparser.models import (
    BBoxInfo,
    ContentElement,
    DocCategory,
    EngineType,
    ParseReport,
    ParseResult,
)


class TestBBoxInfo:
    def test_to_dict(self):
        bbox = BBoxInfo(page=1, x0=10.123, y0=20.456, x1=100.789, y1=200.012)
        d = bbox.to_dict()
        assert d["page"] == 1
        assert d["x0"] == 10.12
        assert d["y1"] == 200.01

    def test_rounding(self):
        bbox = BBoxInfo(page=0, x0=0.005, y0=0.004, x1=0.006, y1=0.009)
        d = bbox.to_dict()
        assert d["x0"] == 0.01
        assert d["y0"] == 0.0


class TestContentElement:
    def test_to_dict_without_bbox(self):
        elem = ContentElement(text="hello world", element_type="paragraph", page=3)
        d = elem.to_dict()
        assert d["element_type"] == "paragraph"
        assert d["page"] == 3
        assert "bbox" not in d

    def test_to_dict_with_bbox(self):
        bbox = BBoxInfo(page=1, x0=0, y0=0, x1=100, y1=100)
        elem = ContentElement(text="x", element_type="heading", page=1, bbox=bbox)
        d = elem.to_dict()
        assert "bbox" in d

    def test_text_truncated_in_dict(self):
        elem = ContentElement(text="a" * 300, element_type="paragraph", page=1)
        d = elem.to_dict()
        assert len(d["text"]) == 200


class TestParseResult:
    def test_success_when_markdown_present(self):
        r = ParseResult(
            source_path=Path("test.pdf"),
            engine=EngineType.DOCLING,
            category=DocCategory.DATASHEET,
            markdown="# Hello",
        )
        assert r.success is True

    def test_failure_when_error_set(self):
        r = ParseResult(
            source_path=Path("test.pdf"),
            engine=EngineType.DOCLING,
            category=DocCategory.DATASHEET,
            markdown="# Hello",
            error="something broke",
        )
        assert r.success is False

    def test_failure_when_empty_markdown(self):
        r = ParseResult(
            source_path=Path("test.pdf"),
            engine=EngineType.DOCLING,
            category=DocCategory.GENERAL,
            markdown="",
        )
        assert r.success is False


class TestParseReport:
    def test_finalize(self):
        r1 = ParseResult(
            source_path=Path("a.pdf"),
            engine=EngineType.DOCLING,
            category=DocCategory.GENERAL,
            markdown="ok",
        )
        r2 = ParseResult(
            source_path=Path("b.pdf"),
            engine=EngineType.MARKER,
            category=DocCategory.GENERAL,
            markdown="",
            error="fail",
        )
        report = ParseReport(results=[r1, r2])
        report.finalize()
        assert report.total_files == 2
        assert report.success_count == 1
        assert report.fail_count == 1
        assert report.total_elapsed_sec >= 0
