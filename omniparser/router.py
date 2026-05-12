"""Router: classify a PDF and select the optimal parsing engine."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from omniparser.models import DocCategory, EngineType

logger = logging.getLogger("omniparser.router")

_DATASHEET_KEYWORDS = re.compile(
    r"(datasheet|user\s*manual|register|aurix|infineon|tricore"
    r"|application\s*note|reference\s*manual|technical\s*reference)",
    re.IGNORECASE,
)

_MATH_INDICATORS = re.compile(
    r"(\\frac|\\int|\\sum|\\partial|\\nabla|\\mathbb"
    r"|equation|theorem|lemma|corollary|\\begin\{align)",
    re.IGNORECASE,
)


class Router:
    """Classify a PDF by its filename and first-page text, then pick an engine.

    Decision matrix:
        - filename or first-page text matches datasheet/register keywords → Docling
        - first-page text has heavy math indicators → MinerU
        - first-page text looks like dual-column academic paper → MinerU
        - everything else → Marker (fast general-purpose)
    """

    def classify(self, pdf_path: Path) -> tuple[DocCategory, EngineType]:
        """Return ``(category, engine)`` for *pdf_path*."""
        name_lower = pdf_path.stem.lower()
        first_page = self._read_first_page(pdf_path)
        combined = f"{name_lower} {first_page}"

        if _DATASHEET_KEYWORDS.search(combined):
            cat = DocCategory.DATASHEET
            engine = EngineType.DOCLING
        elif self._is_math_heavy(first_page):
            cat = DocCategory.MATH_HEAVY
            engine = EngineType.MINERU
        elif self._is_dual_column(first_page):
            cat = DocCategory.DUAL_COLUMN
            engine = EngineType.MINERU
        else:
            cat = DocCategory.GENERAL
            engine = EngineType.MARKER

        logger.info(
            "Routed %s → category=%s engine=%s",
            pdf_path.name, cat.value, engine.value,
        )
        return cat, engine

    # ------------------------------------------------------------------
    # Heuristics
    # ------------------------------------------------------------------

    @staticmethod
    def _read_first_page(pdf_path: Path) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            if reader.pages:
                return reader.pages[0].extract_text() or ""
        except Exception:
            pass
        return ""

    @staticmethod
    def _is_math_heavy(text: str) -> bool:
        hits = len(_MATH_INDICATORS.findall(text))
        return hits >= 3

    @staticmethod
    def _is_dual_column(text: str) -> bool:
        lines = text.splitlines()
        if len(lines) < 10:
            return False
        short = sum(1 for ln in lines if 5 < len(ln.strip()) < 45)
        return short / len(lines) > 0.6
