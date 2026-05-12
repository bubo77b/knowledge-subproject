"""Tests for omniparser.config."""

from pathlib import Path

from omniparser.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.input_dir == Path("./input")
        assert s.output_dir == Path("./output")
        assert s.gpu_memory_limit_mb == 14000
        assert s.max_workers == 2
        assert s.llm_enabled is False

    def test_override(self):
        s = Settings(max_workers=4, llm_enabled=True, llm_model="qwen2.5")
        assert s.max_workers == 4
        assert s.llm_enabled is True
        assert s.llm_model == "qwen2.5"
