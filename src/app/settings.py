from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    project_name: str = "MinerU Knowledge Skill"
    output_dir: Path = Path("./outputs/markdown")
    assets_dir: Path = Path("./outputs/assets")
    chroma_path: Path = Path("./outputs/chroma")
    chroma_collection: str = "personal_knowledge"
    obsidian_vault_path: Path = Path("./outputs/obsidian_vault")
    obsidian_managed_block_start: str = "<!-- AI_MANAGED_START -->"
    obsidian_managed_block_end: str = "<!-- AI_MANAGED_END -->"
    mineru_enabled: bool = True
    mineru_timeout_seconds: int = 120
    chunk_size: int = 800
    chunk_overlap: int = 120
    context_top_k: int = 6
    keyword_min_len: int = 4
    keyword_top_k: int = 12
    synonym_map: dict[str, str] = Field(default_factory=dict)


def load_settings(path: str | Path = "config/settings.yaml") -> AppSettings:
    raw: dict[str, Any] = {}
    cfg_path = Path(path)
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    settings = AppSettings(**raw)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.assets_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    settings.obsidian_vault_path.mkdir(parents=True, exist_ok=True)
    return settings
