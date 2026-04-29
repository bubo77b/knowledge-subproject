# MinerU Knowledge Skill

A Python toolchain that converts mixed documents to Markdown, stores knowledge in ChromaDB, and syncs notes to Obsidian with bidirectional links.

## Features

- `CLI + REST` dual entrypoints for local use and AI assistant integration.
- MinerU-first parsing with robust fallback parsers.
- Markdown normalization for cleaner headings and structure.
- ChromaDB ingestion and retrieval APIs for RAG context building.
- Obsidian note generation with wiki-link and backlink support.

## Quick Start

1. Install dependencies:

   ```bash
   pip install -e .[dev]
   ```

2. Configure settings:

   - Edit `config/settings.yaml`.

3. Run CLI:

   ```bash
   knowledge-skill ingest ./docs --to-markdown --to-chroma --to-obsidian
   ```

4. Run REST API:

   ```bash
   uvicorn src.app.main:app --reload --port 8000
   ```

## CLI Examples

- Parse to Markdown only:
  - `knowledge-skill ingest ./docs --to-markdown`
- Parse + ingest into ChromaDB:
  - `knowledge-skill ingest ./docs --to-markdown --to-chroma`
- Search knowledge base:
  - `knowledge-skill search "transformer attention"`

## REST Endpoints

- `POST /ingest`
- `POST /search`
- `POST /retrieve_context`
- `GET /health`

## Testing

```bash
pytest
```
<<<<<<< HEAD
=======
# MinerU Knowledge Skill

A Python toolchain that converts mixed documents to Markdown, stores knowledge in ChromaDB, and syncs notes to Obsidian with bidirectional links.

## Features

- `CLI + REST` dual entrypoints for local use and AI assistant integration.
- MinerU-first parsing with robust fallback parsers.
- Markdown normalization for cleaner headings and structure.
- ChromaDB ingestion and retrieval APIs for RAG context building.
- Obsidian note generation with wiki-link and backlink support.

## Quick Start

1. Install dependencies:

   ```bash
   pip install -e .[dev]
   ```

2. Configure settings:

   - Edit `config/settings.yaml`.

3. Run CLI:

   ```bash
   knowledge-skill ingest ./docs --to-markdown --to-chroma --to-obsidian
   ```

4. Run REST API:

   ```bash
   uvicorn src.app.main:app --reload --port 8000
   ```

## CLI Examples

- Parse to Markdown only:
  - `knowledge-skill ingest ./docs --to-markdown`
- Parse + ingest into ChromaDB:
  - `knowledge-skill ingest ./docs --to-markdown --to-chroma`
- Search knowledge base:
  - `knowledge-skill search "transformer attention"`

## REST Endpoints

- `POST /ingest`
- `POST /search`
- `POST /retrieve_context`
- `GET /health`

## Testing

```bash
pytest
```
>>>>>>> 1c9f9dd (Build initial MinerU knowledge skill scaffold with parsing, retrieval, and Obsidian sync.)
# Knowledge Subproject (文档到 Obsidian 知识管道)

这是一个按你要求重构的完整版本：  
**多引擎文档转 Markdown + 图表识别位点 + AI 分析 + Obsidian 双链知识库**。

## 架构

1. 解析层（PDF 优先）：按 `PARSER_ORDER` 顺序尝试
<<<<<<< HEAD
   - `mineru`
=======
   - `mineru`（优先）
>>>>>>> 1c9f9dd (Build initial MinerU knowledge skill scaffold with parsing, retrieval, and Obsidian sync.)
   - `paddleocr`
   - 都失败时可回退到 `pypdf`（可配置）
   - 超大 PDF（页数超阈值）自动走 `pypdf` 分页批处理，避免内存和超时问题
2. 分析层：
   - `LLM_PROVIDER=openai/ollama/none`
   - 自动提取摘要、标签、实体、关键点、关联主题
3. 图表层：
   - 内置图表线索检测（表格线、figure 引用）
   - `CHART_EXTRACTOR=deplot/unichart` 作为可插拔策略开关
4. 存储层：
   - SQLite 记录文档、笔记、链接关系、解析器来源
5. 笔记层：
   - 写入 Obsidian Markdown
   - 自动生成双向 wikilink/backlink

## 快速开始

```bash
<<<<<<< HEAD
=======
py -3.12 -m venv .venv
.\.venv\Scripts\activate
>>>>>>> 1c9f9dd (Build initial MinerU knowledge skill scaffold with parsing, retrieval, and Obsidian sync.)
pip install -r requirements.txt
copy .env.example .env
python -m knowledge_pipeline.cli --print-config
python -m knowledge_pipeline.cli
```

## `.env` 关键项

<<<<<<< HEAD
- `PARSER_ORDER=mineru,marker,paddleocr`
=======
- `PARSER_ORDER=mineru,paddleocr`
- `MINERU_EXECUTABLE=./.venv312-mineru/Scripts/mineru.exe`（推荐 Python 3.12 专用环境）
- `MINERU_API_URL=`（可选，指向已启动的 `mineru-api`，例如 `http://127.0.0.1:59111`）
- `MINERU_BACKEND=pipeline`
- `MINERU_METHOD=txt`
- `MINERU_DISABLE_PROXY=true`（避免本地 API 被代理劫持导致 502）
>>>>>>> 1c9f9dd (Build initial MinerU knowledge skill scaffold with parsing, retrieval, and Obsidian sync.)
- `PARSER_TIMEOUT_SECONDS=120`
- `FALLBACK_PARSER_ENABLED=true`
- `LARGE_PDF_PAGE_THRESHOLD=300`
- `PDF_BATCH_PAGES=50`
- `CHART_EXTRACTOR=none|deplot|unichart`
- `LLM_PROVIDER=none|openai|ollama`
- `LLM_ENABLED=true|false`
- `LLM_BASE_URL`（Ollama 默认自动补 `http://localhost:11434/v1`）
- `AI_CHUNK_SIZE_CHARS=6000`
- `AI_CHUNK_OVERLAP_CHARS=600`
- `AI_MAX_CHUNKS=120`

## Ollama 示例

```env
LLM_PROVIDER=ollama
LLM_ENABLED=true
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5:7b
```

<<<<<<< HEAD
=======
## Windows 上 MinerU 优先推荐

```bash
py -3.12 -m venv .venv312-mineru
.\.venv312-mineru\Scripts\python -m pip install -U pip
.\.venv312-mineru\Scripts\python -m pip install "mineru[all]"
```

然后在 `.env` 中设置：

```env
PARSER_ORDER=mineru,paddleocr
MINERU_EXECUTABLE=./.venv312-mineru/Scripts/mineru.exe
```

>>>>>>> 1c9f9dd (Build initial MinerU knowledge skill scaffold with parsing, retrieval, and Obsidian sync.)
## 产物

- Obsidian 笔记：`<vault>/<notes_subdir>/<note_id>.md`
- SQLite：`documents / notes / links`
- 每篇笔记 frontmatter 含 `parser_used`，便于你后续做质量追踪与再处理

## 运行时进度日志

运行 `python -m knowledge_pipeline.cli` 时会输出实时日志：

- `[knowledge-pipeline]`：文件级进度、跳过/失败、总耗时
- `[parser]`：当前解析器尝试、页数、分页提取进度、命令执行状态
- `[analyzer]`：文本分块数量、每块分析进度、回退策略

## 关于 Pillow 与替代方案

- `MinerU` 近期依赖会把 `Pillow` 升级到 `12.x`
- `Marker/Surya` 常要求 `Pillow < 11`
- 如果你想保持当前 `Pillow`，推荐方案是：
  - 主链路只保留 `MinerU + pypdf + PaddleOCR`
  - `Marker/Surya` 放到单独虚拟环境（通过子进程调用）

