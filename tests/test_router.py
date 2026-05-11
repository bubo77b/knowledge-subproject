"""Tests for omniparser.router."""

from pathlib import Path
from unittest.mock import patch

from omniparser.models import DocCategory, EngineType
from omniparser.router import Router


class TestRouter:
    def setup_method(self):
        self.router = Router()

    @patch.object(Router, "_read_first_page", return_value="")
    def test_datasheet_keyword_in_filename(self, _mock):
        cat, eng = self.router.classify(Path("TC375_Datasheet_v1.2.pdf"))
        assert cat == DocCategory.DATASHEET
        assert eng == EngineType.DOCLING

    @patch.object(Router, "_read_first_page", return_value="")
    def test_user_manual_keyword(self, _mock):
        cat, eng = self.router.classify(Path("AURIX_User_Manual.pdf"))
        assert cat == DocCategory.DATASHEET
        assert eng == EngineType.DOCLING

    @patch.object(Router, "_read_first_page", return_value="")
    def test_register_keyword(self, _mock):
        cat, eng = self.router.classify(Path("Register_Map.pdf"))
        assert cat == DocCategory.DATASHEET
        assert eng == EngineType.DOCLING

    @patch.object(Router, "_read_first_page", return_value="")
    def test_infineon_keyword(self, _mock):
        cat, eng = self.router.classify(Path("infineon_app_note.pdf"))
        assert cat == DocCategory.DATASHEET
        assert eng == EngineType.DOCLING

    @patch.object(
        Router, "_read_first_page",
        return_value=(
            "\\frac{a}{b} \\int_0^1 \\sum_{i=0}^n "
            "\\partial f \\nabla g equation theorem"
        ),
    )
    def test_math_heavy_routes_to_mineru(self, _mock):
        cat, eng = self.router.classify(Path("paper.pdf"))
        assert cat == DocCategory.MATH_HEAVY
        assert eng == EngineType.MINERU

    @patch.object(
        Router, "_read_first_page",
        return_value="\n".join(["short line"] * 20),
    )
    def test_dual_column_routes_to_mineru(self, _mock):
        cat, eng = self.router.classify(Path("ieee_paper.pdf"))
        assert cat == DocCategory.DUAL_COLUMN
        assert eng == EngineType.MINERU

    @patch.object(Router, "_read_first_page", return_value="Just a normal document text here.")
    def test_general_routes_to_marker(self, _mock):
        cat, eng = self.router.classify(Path("notes.pdf"))
        assert cat == DocCategory.GENERAL
        assert eng == EngineType.MARKER

    @patch.object(
        Router, "_read_first_page",
        return_value="This document describes the Register interface for Infineon AURIX MCU.",
    )
    def test_first_page_content_triggers_datasheet(self, _mock):
        cat, eng = self.router.classify(Path("unknown_name.pdf"))
        assert cat == DocCategory.DATASHEET
        assert eng == EngineType.DOCLING
