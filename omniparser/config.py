"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """OmniParser runtime settings.

    Values are read from environment variables or a `.env` file located
    in the current working directory.
    """

    # Directories
    input_dir: Path = Field(default=Path("./input"))
    output_dir: Path = Field(default=Path("./output"))

    # GPU
    gpu_memory_limit_mb: int = Field(default=14000)
    gpu_monitor_interval_sec: int = Field(default=2)

    # Batch processing
    max_workers: int = Field(default=2)

    # LLM post-processing
    llm_enabled: bool = Field(default=False)
    llm_provider: str = Field(default="ollama")
    llm_base_url: str = Field(default="http://localhost:11434/v1")
    llm_api_key: str = Field(default="ollama")
    llm_model: str = Field(default="llama3")

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="omniparser.log")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


