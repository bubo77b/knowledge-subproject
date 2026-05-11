"""Multi-engine PDF parsing: Docling (primary), MinerU, Marker, pypdf fallback."""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from omniparser.models import (
    BBoxInfo,
    ContentElement,
    DocCategory,
    EngineType,
    PageRange,
    ParseResult,
)

logger = logging.getLogger("omniparser.engine")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseEngine(ABC):
    """Interface every parsing engine must implement."""

    engine_type: EngineType

    @abstractmethod
    def parse(
        self, pdf_path: Path, *, page_range: PageRange | None = None,
    ) -> ParseResult:
        """Parse *pdf_path* and return a ``ParseResult``.

        Args:
            pdf_path: Path to the PDF file.
            page_range: Optional 1-based inclusive page range to extract.
                When ``None``, the entire document is processed.
        """

    # Shared helpers ---------------------------------------------------------

    @staticmethod
    def _count_tables(md: str) -> int:
        return len(re.findall(r"^\|.*\|$", md, re.MULTILINE)) // 3  # heuristic: ~3 rows/table

    @staticmethod
    def _count_formulas(md: str) -> int:
        block = len(re.findall(r"\$\$.+?\$\$", md, re.DOTALL))
        inline = len(re.findall(r"(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)", md))
        return block + inline


# ---------------------------------------------------------------------------
# Engine A — Docling (primary for datasheets / register docs)
# ---------------------------------------------------------------------------

class DoclingEngine(BaseEngine):
    """Docling-based parser with deep table-structure support."""

    engine_type = EngineType.DOCLING

    def parse(
        self, pdf_path: Path, *, page_range: PageRange | None = None,
    ) -> ParseResult:
        t0 = time.monotonic()
        elements: list[ContentElement] = []
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()

            convert_kwargs: dict = {"source": str(pdf_path)}
            if page_range is not None:
                convert_kwargs["page_range"] = (page_range.start, page_range.end)

            result = converter.convert(**convert_kwargs)
            doc = result.document

            md = doc.export_to_markdown()

            for i, item in enumerate(doc.texts):
                page_no = self._extract_page_number(item, i)
                bbox = self._extract_bbox(item, page_no)
                elements.append(ContentElement(
                    text=item.text if hasattr(item, "text") else str(item),
                    element_type=self._classify_element(item),
                    page=page_no,
                    bbox=bbox,
                ))

            page_count = self._get_page_count(doc, pdf_path)
            if page_range is not None:
                total_pages = page_count
                page_count = min(page_range.end, total_pages) - page_range.start + 1
                page_count = max(page_count, 0)

            elapsed = time.monotonic() - t0
            pr_label = f" pages={page_range}" if page_range else ""
            logger.info(
                "Docling parsed %s%s: %d pages, %d elements in %.1fs",
                pdf_path.name, pr_label, page_count, len(elements), elapsed,
            )
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.DATASHEET,
                markdown=md,
                elements=elements,
                page_count=page_count,
                table_count=self._count_tables(md),
                formula_count=self._count_formulas(md),
                elapsed_sec=elapsed,
                page_range=page_range,
            )
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error("Docling failed on %s: %s", pdf_path.name, exc)
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.DATASHEET,
                markdown="",
                elapsed_sec=elapsed,
                error=str(exc),
                page_range=page_range,
            )

    @staticmethod
    def _extract_page_number(item: object, fallback: int) -> int:
        for attr in ("page_no", "page", "prov"):
            val = getattr(item, attr, None)
            if val is None:
                continue
            if isinstance(val, int):
                return val
            if isinstance(val, list) and val:
                prov = val[0]
                pn = getattr(prov, "page_no", None) or getattr(prov, "page", None)
                if isinstance(pn, int):
                    return pn
        return fallback

    @staticmethod
    def _extract_bbox(item: object, page: int) -> BBoxInfo | None:
        prov = getattr(item, "prov", None)
        if isinstance(prov, list) and prov:
            bbox = getattr(prov[0], "bbox", None)
            if bbox is not None:
                coords = (
                    getattr(bbox, "l", 0),
                    getattr(bbox, "t", 0),
                    getattr(bbox, "r", 0),
                    getattr(bbox, "b", 0),
                )
                if any(c != 0 for c in coords):
                    return BBoxInfo(page=page, x0=coords[0], y0=coords[1],
                                   x1=coords[2], y1=coords[3])
        return None

    @staticmethod
    def _classify_element(item: object) -> str:
        label = getattr(item, "label", "") or ""
        label_lower = label.lower() if isinstance(label, str) else ""
        if "heading" in label_lower or "title" in label_lower:
            return "heading"
        if "table" in label_lower:
            return "table"
        if "formula" in label_lower or "equation" in label_lower:
            return "formula"
        if "list" in label_lower:
            return "list"
        if "figure" in label_lower or "image" in label_lower:
            return "image"
        return "paragraph"

    @staticmethod
    def _get_page_count(doc: object, pdf_path: Path) -> int:
        pc = getattr(doc, "num_pages", None) or getattr(doc, "page_count", None)
        if isinstance(pc, int) and pc > 0:
            return pc
        try:
            from pypdf import PdfReader
            return len(PdfReader(str(pdf_path)).pages)
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Engine B-1 — MinerU (math-heavy / dual-column)
# ---------------------------------------------------------------------------

class MinerUEngine(BaseEngine):
    """MinerU engine for formula-rich or dual-column documents.

    MinerU (magic-pdf) is invoked via subprocess so it can run in its own
    Python environment if needed.
    """

    engine_type = EngineType.MINERU

    def parse(
        self, pdf_path: Path, *, page_range: PageRange | None = None,
    ) -> ParseResult:
        t0 = time.monotonic()
        elements: list[ContentElement] = []
        try:
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = [
                    "mineru", str(pdf_path),
                    "-o", tmpdir,
                    "-m", "txt",
                ]
                if page_range is not None:
                    cmd.extend(["-p", str(page_range)])

                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=600,
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"mineru exited {proc.returncode}: {proc.stderr[:500]}"
                    )
                md_files = list(Path(tmpdir).rglob("*.md"))
                if not md_files:
                    raise FileNotFoundError("MinerU produced no markdown output")

                md = md_files[0].read_text(encoding="utf-8")
                elements = self._elements_from_markdown(md)

            page_count = self._page_count(pdf_path)
            if page_range is not None:
                page_count = min(page_range.end, page_count) - page_range.start + 1
                page_count = max(page_count, 0)

            elapsed = time.monotonic() - t0
            pr_label = f" pages={page_range}" if page_range else ""
            logger.info(
                "MinerU parsed %s%s: %d pages in %.1fs",
                pdf_path.name, pr_label, page_count, elapsed,
            )
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.MATH_HEAVY,
                markdown=md,
                elements=elements,
                page_count=page_count,
                table_count=self._count_tables(md),
                formula_count=self._count_formulas(md),
                elapsed_sec=elapsed,
                page_range=page_range,
            )
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error("MinerU failed on %s: %s", pdf_path.name, exc)
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.MATH_HEAVY,
                markdown="",
                elapsed_sec=elapsed,
                error=str(exc),
                page_range=page_range,
            )

    @staticmethod
    def _page_count(pdf_path: Path) -> int:
        try:
            from pypdf import PdfReader
            return len(PdfReader(str(pdf_path)).pages)
        except Exception:
            return 0

    @staticmethod
    def _elements_from_markdown(md: str) -> list[ContentElement]:
        elements: list[ContentElement] = []
        for line in md.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                etype = "heading"
            elif stripped.startswith("|"):
                etype = "table"
            elif "$$" in stripped or re.search(r"(?<!\$)\$(?!\$)", stripped):
                etype = "formula"
            else:
                etype = "paragraph"
            elements.append(ContentElement(text=stripped, element_type=etype, page=0))
        return elements


# ---------------------------------------------------------------------------
# Engine B-2 — Marker (general / fast)
# ---------------------------------------------------------------------------

class MarkerEngine(BaseEngine):
    """Marker engine for general-purpose fast conversion."""

    engine_type = EngineType.MARKER

    def parse(
        self, pdf_path: Path, *, page_range: PageRange | None = None,
    ) -> ParseResult:
        t0 = time.monotonic()
        elements: list[ContentElement] = []
        try:
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = [
                    "marker_single", str(pdf_path),
                    tmpdir,
                ]
                if page_range is not None:
                    cmd.extend(["--page_range", str(page_range)])

                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=600,
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"marker exited {proc.returncode}: {proc.stderr[:500]}"
                    )

                md_files = list(Path(tmpdir).rglob("*.md"))
                if not md_files:
                    raise FileNotFoundError("Marker produced no markdown output")

                md = md_files[0].read_text(encoding="utf-8")
                elements = MinerUEngine._elements_from_markdown(md)

            page_count = MinerUEngine._page_count(pdf_path)
            if page_range is not None:
                page_count = min(page_range.end, page_count) - page_range.start + 1
                page_count = max(page_count, 0)

            elapsed = time.monotonic() - t0
            pr_label = f" pages={page_range}" if page_range else ""
            logger.info(
                "Marker parsed %s%s: %d pages in %.1fs",
                pdf_path.name, pr_label, page_count, elapsed,
            )
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.GENERAL,
                markdown=md,
                elements=elements,
                page_count=page_count,
                table_count=self._count_tables(md),
                formula_count=self._count_formulas(md),
                elapsed_sec=elapsed,
                page_range=page_range,
            )
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error("Marker failed on %s: %s", pdf_path.name, exc)
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.GENERAL,
                markdown="",
                elapsed_sec=elapsed,
                error=str(exc),
                page_range=page_range,
            )


# ---------------------------------------------------------------------------
# Fallback — pypdf (always available)
# ---------------------------------------------------------------------------

class PyPDFEngine(BaseEngine):
    """Minimal text-only extraction via pypdf — last-resort fallback."""

    engine_type = EngineType.DOCLING  # reported as docling-fallback in logs

    def parse(
        self, pdf_path: Path, *, page_range: PageRange | None = None,
    ) -> ParseResult:
        t0 = time.monotonic()
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            all_pages = reader.pages

            if page_range is not None:
                selected = list(enumerate(all_pages[page_range.to_0based_slice()],
                                          start=page_range.start))
            else:
                selected = list(enumerate(all_pages, start=1))

            pages_text: list[tuple[int, str]] = []
            elements: list[ContentElement] = []

            for page_num, page in selected:
                text = page.extract_text() or ""
                pages_text.append((page_num, text))
                if text.strip():
                    elements.append(ContentElement(
                        text=text.strip()[:500],
                        element_type="paragraph",
                        page=page_num,
                    ))

            md = "\n\n---\n\n".join(
                f"<!-- Page {pn} -->\n\n{t}"
                for pn, t in pages_text if t.strip()
            )
            extracted_count = len(selected)
            elapsed = time.monotonic() - t0
            pr_label = f" pages={page_range}" if page_range else ""
            logger.info(
                "pypdf fallback parsed %s%s: %d pages in %.1fs",
                pdf_path.name, pr_label, extracted_count, elapsed,
            )
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.GENERAL,
                markdown=md,
                elements=elements,
                page_count=extracted_count,
                table_count=0,
                formula_count=0,
                elapsed_sec=elapsed,
                page_range=page_range,
            )
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error("pypdf fallback failed on %s: %s", pdf_path.name, exc)
            return ParseResult(
                source_path=pdf_path,
                engine=self.engine_type,
                category=DocCategory.GENERAL,
                markdown="",
                elapsed_sec=elapsed,
                error=str(exc),
                page_range=page_range,
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_engine(engine_type: EngineType) -> BaseEngine:
    """Return the engine instance for the given type."""
    engines: dict[EngineType, type[BaseEngine]] = {
        EngineType.DOCLING: DoclingEngine,
        EngineType.MINERU: MinerUEngine,
        EngineType.MARKER: MarkerEngine,
    }
    cls = engines.get(engine_type)
    if cls is None:
        raise ValueError(f"Unknown engine: {engine_type}")
    return cls()


def get_fallback_engine() -> BaseEngine:
    """Return the pypdf fallback engine."""
    return PyPDFEngine()
