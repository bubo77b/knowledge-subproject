# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

OmniParser is an industrial-grade PDF-to-Markdown preprocessing system with multi-engine routing (Docling / MinerU / Marker), GPU-aware batch processing, and optional LLM post-processing. See `README.md` for CLI usage and architecture details.

### Running tests

```bash
pytest
```

All 52 tests are self-contained and require no external services, GPU, or PDF parsing engines beyond pypdf. Tests cover: models, config, router, postprocessor, parser engine helpers, GPU monitor (graceful no-GPU), and batch processing (end-to-end with pypdf fallback).

### Linting

```bash
ruff check omniparser/ tests/ --select E,F,W,I
```

### Running the CLI

```bash
# Single file (auto-routes based on filename/content)
omniparser single input/some.pdf -o ./output

# Batch mode
omniparser run ./input -o ./output -w 2

# Force a specific engine
omniparser single paper.pdf -e docling
```

### Environment notes

- Python 3.11+ required (`requires-python = ">=3.11"`).
- Install in dev mode: `pip install -e ".[dev]"`.
- Docling downloads HuggingFace models on first run (~770 weights, takes ~5s). Subsequent runs use cache.
- RapidOCR models are also auto-downloaded on first Docling invocation.
- The GPU monitor degrades gracefully on CPU-only machines (all GPU checks return safe).
- MinerU and Marker engines invoke external CLI tools via subprocess. They are not installed by default — the system falls back to pypdf when they are unavailable.
- `fpdf2` is only needed for creating test PDFs, not a runtime dependency.
