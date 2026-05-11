"""Data models for OmniParser pipeline."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class EngineType(str, Enum):
    """Supported parsing engines."""

    DOCLING = "docling"
    MINERU = "mineru"
    MARKER = "marker"


class DocCategory(str, Enum):
    """Document categories determined by the router."""

    DATASHEET = "datasheet"
    MATH_HEAVY = "math_heavy"
    DUAL_COLUMN = "dual_column"
    GENERAL = "general"


@dataclass(frozen=True)
class PageRange:
    """An inclusive page range (1-based).

    Examples:
        ``PageRange(1, 50)`` → pages 1 through 50.
        ``PageRange(100, 100)`` → page 100 only.
    """

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1:
            raise ValueError(f"start must be >= 1, got {self.start}")
        if self.end < self.start:
            raise ValueError(
                f"end ({self.end}) must be >= start ({self.start})"
            )

    @property
    def page_count(self) -> int:
        return self.end - self.start + 1

    def to_0based_slice(self) -> slice:
        """Return a 0-based slice suitable for indexing a list of pages."""
        return slice(self.start - 1, self.end)

    def contains(self, page_1based: int) -> bool:
        """Return True if *page_1based* falls within this range."""
        return self.start <= page_1based <= self.end

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


def parse_page_range(spec: str) -> PageRange:
    """Parse a page-range string into a ``PageRange``.

    Supported formats:
        ``"10-50"``   → pages 10 through 50
        ``"10"``      → page 10 only
        ``"10-"``     → pages 10 to end (end = 999_999_999)
        ``"-50"``     → pages 1 through 50
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("Empty page range")

    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", spec)
    if m:
        return PageRange(int(m.group(1)), int(m.group(2)))

    m = re.fullmatch(r"(\d+)\s*-\s*", spec)
    if m:
        return PageRange(int(m.group(1)), 999_999_999)

    m = re.fullmatch(r"-\s*(\d+)", spec)
    if m:
        return PageRange(1, int(m.group(1)))

    m = re.fullmatch(r"(\d+)", spec)
    if m:
        val = int(m.group(1))
        return PageRange(val, val)

    raise ValueError(f"Invalid page range: {spec!r}")


@dataclass
class BBoxInfo:
    """Bounding box for a content element on a page."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "x0": round(self.x0, 2),
            "y0": round(self.y0, 2),
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
        }


@dataclass
class ContentElement:
    """A single parsed content element with location metadata."""

    text: str
    element_type: str  # heading, paragraph, table, formula, image, list, etc.
    page: int
    bbox: BBoxInfo | None = None

    def to_dict(self) -> dict:
        result: dict = {
            "text": self.text[:200],
            "element_type": self.element_type,
            "page": self.page,
        }
        if self.bbox:
            result["bbox"] = self.bbox.to_dict()
        return result


@dataclass
class ParseResult:
    """Result of parsing a single PDF file."""

    source_path: Path
    engine: EngineType
    category: DocCategory
    markdown: str
    elements: list[ContentElement] = field(default_factory=list)
    page_count: int = 0
    table_count: int = 0
    formula_count: int = 0
    image_count: int = 0
    image_paths: list[Path] = field(default_factory=list)
    elapsed_sec: float = 0.0
    error: str | None = None
    page_range: PageRange | None = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.markdown) > 0


@dataclass
class ParseReport:
    """Aggregated report for a batch run."""

    total_files: int = 0
    success_count: int = 0
    fail_count: int = 0
    total_elapsed_sec: float = 0.0
    results: list[ParseResult] = field(default_factory=list)
    _start: float = field(default_factory=time.monotonic, repr=False)

    def finalize(self) -> None:
        self.total_elapsed_sec = time.monotonic() - self._start
        self.total_files = len(self.results)
        self.success_count = sum(1 for r in self.results if r.success)
        self.fail_count = self.total_files - self.success_count
