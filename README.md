# OmniParser

Industrial-grade PDF-to-Markdown preprocessing system with multi-engine routing, GPU-aware batch processing, and optional LLM post-processing.

## Architecture

```
PDF → Router → Engine A (Docling)  ─┐
                Engine B1 (MinerU) ─┤→ Markdown → PostProcessor → LLM (optional) → .md + .json
                Engine B2 (Marker) ─┤
                Fallback (pypdf)   ─┘
```

### Engine Routing

| Document Type | Detection | Engine |
|---|---|---|
| Datasheets / Register docs | filename or first-page keywords (datasheet, user manual, register, AURIX, Infineon) | **Docling** |
| Math-heavy papers | LaTeX indicators on first page (≥3 hits) | **MinerU** |
| Dual-column papers | short-line heuristic on first page | **MinerU** |
| General documents | everything else | **Marker** |

If the selected engine fails, **pypdf** is used as a last-resort fallback.

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env

# Batch processing
omniparser run ./input -o ./output

# Single file
omniparser single paper.pdf -o ./output

# With LLM post-processing
omniparser single paper.pdf --llm
```

## CLI Commands

- `omniparser run <input_dir>` — batch-convert all PDFs in a folder
- `omniparser single <file.pdf>` — process one file
- `omniparser version` — print version

## Output

For each PDF, two files are produced:

- `<name>.md` — clean Markdown with normalised headings, tables, and LaTeX
- `<name>.json` — metadata including page numbers, bounding boxes, engine used, and element-level details

## Configuration

Copy `.env.example` to `.env` and adjust values. Key settings:

| Variable | Default | Description |
|---|---|---|
| `GPU_MEMORY_LIMIT_MB` | 14000 | Max GPU memory before throttling |
| `MAX_WORKERS` | 2 | Parallel worker processes |
| `LLM_ENABLED` | false | Enable LLM-based Markdown cleanup |
| `LLM_MODEL` | llama3 | Model for post-processing |

## Testing

```bash
pytest
```
