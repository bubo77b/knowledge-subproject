"""Batch processor: parallel PDF processing with GPU-aware scheduling."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from omniparser.config import Settings
from omniparser.gpu_monitor import GPUMonitor
from omniparser.models import PageRange, ParseReport, ParseResult
from omniparser.parser_engine import get_engine, get_fallback_engine
from omniparser.postprocessor import LLMPostProcessor, MarkdownPostProcessor
from omniparser.router import Router

logger = logging.getLogger("omniparser.batch")


def _process_single(
    pdf_path_str: str,
    settings_dict: dict,
    page_range_tuple: tuple[int, int] | None = None,
) -> dict:
    """Worker function executed in a subprocess.

    Accepts and returns plain dicts / strings so it can be pickled across
    process boundaries.
    """
    import logging as _log
    _log.basicConfig(level=settings_dict.get("log_level", "INFO"))

    from omniparser.config import Settings as _S
    from omniparser.models import PageRange

    settings = _S(**settings_dict)
    pdf_path = Path(pdf_path_str)
    pr = PageRange(*page_range_tuple) if page_range_tuple else None

    router = Router()
    postproc = MarkdownPostProcessor()
    llm_postproc = LLMPostProcessor(settings)

    category, engine_type = router.classify(pdf_path)
    engine = get_engine(engine_type)
    result = engine.parse(pdf_path, page_range=pr)

    if not result.success:
        _log.getLogger("omniparser.batch").warning(
            "Primary engine %s failed on %s, trying fallback",
            engine_type.value, pdf_path.name,
        )
        fallback = get_fallback_engine()
        result = fallback.parse(pdf_path, page_range=pr)

    result.category = category

    if result.success:
        result.markdown = postproc.process(result.markdown)
        result.markdown = llm_postproc.process(result.markdown)

    return {
        "source_path": str(result.source_path),
        "engine": result.engine.value,
        "category": result.category.value,
        "markdown": result.markdown,
        "page_count": result.page_count,
        "table_count": result.table_count,
        "formula_count": result.formula_count,
        "elapsed_sec": result.elapsed_sec,
        "error": result.error,
        "elements": [e.to_dict() for e in result.elements],
        "page_range": (pr.start, pr.end) if pr else None,
    }


class BatchProcessor:
    """Orchestrate parallel PDF processing for an input directory."""

    def __init__(
        self,
        settings: Settings,
        page_range: PageRange | None = None,
    ) -> None:
        self._settings = settings
        self._page_range = page_range
        self._gpu = GPUMonitor(
            limit_mb=settings.gpu_memory_limit_mb,
            interval_sec=settings.gpu_monitor_interval_sec,
        )

    def run(self, input_dir: Path | None = None) -> ParseReport:
        """Scan *input_dir* for PDFs and process them in parallel."""
        input_dir = input_dir or self._settings.input_dir
        output_dir = self._settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        pdfs = sorted(input_dir.glob("*.pdf"))
        if not pdfs:
            logger.warning("No PDF files found in %s", input_dir)
            return ParseReport()

        logger.info("Found %d PDF(s) in %s", len(pdfs), input_dir)
        self._gpu.start()

        report = ParseReport()
        settings_dict = self._settings.model_dump()
        pr_tuple = (
            (self._page_range.start, self._page_range.end)
            if self._page_range else None
        )

        try:
            if self._settings.max_workers <= 1:
                results = self._run_sequential(
                    pdfs, settings_dict, output_dir, pr_tuple,
                )
            else:
                results = self._run_parallel(
                    pdfs, settings_dict, output_dir, pr_tuple,
                )
            report.results = results
        finally:
            self._gpu.stop()

        report.finalize()
        self._write_report(report, output_dir)
        return report

    # ------------------------------------------------------------------

    def _run_sequential(
        self,
        pdfs: list[Path],
        settings_dict: dict,
        output_dir: Path,
        pr_tuple: tuple[int, int] | None,
    ) -> list[ParseResult]:
        results: list[ParseResult] = []
        for pdf in pdfs:
            self._gpu.wait_until_safe()
            raw = _process_single(str(pdf), settings_dict, pr_tuple)
            result = self._raw_to_result(raw)
            self._write_outputs(result, raw, output_dir)
            results.append(result)
        return results

    def _run_parallel(
        self,
        pdfs: list[Path],
        settings_dict: dict,
        output_dir: Path,
        pr_tuple: tuple[int, int] | None,
    ) -> list[ParseResult]:
        results: list[ParseResult] = []
        with ProcessPoolExecutor(max_workers=self._settings.max_workers) as pool:
            futures = {}
            for pdf in pdfs:
                self._gpu.wait_until_safe()
                fut = pool.submit(
                    _process_single, str(pdf), settings_dict, pr_tuple,
                )
                futures[fut] = pdf

            for fut in as_completed(futures):
                pdf = futures[fut]
                try:
                    raw = fut.result()
                    result = self._raw_to_result(raw)
                    self._write_outputs(result, raw, output_dir)
                    results.append(result)
                except Exception as exc:
                    logger.error("Worker crashed on %s: %s", pdf.name, exc)
                    from omniparser.models import DocCategory, EngineType
                    results.append(ParseResult(
                        source_path=pdf,
                        engine=EngineType.DOCLING,
                        category=DocCategory.GENERAL,
                        markdown="",
                        error=str(exc),
                    ))
        return results

    # ------------------------------------------------------------------

    @staticmethod
    def _raw_to_result(raw: dict) -> ParseResult:
        from omniparser.models import DocCategory, EngineType
        pr_tuple = raw.get("page_range")
        pr = PageRange(*pr_tuple) if pr_tuple else None
        return ParseResult(
            source_path=Path(raw["source_path"]),
            engine=EngineType(raw["engine"]),
            category=DocCategory(raw["category"]),
            markdown=raw["markdown"],
            page_count=raw["page_count"],
            table_count=raw["table_count"],
            formula_count=raw["formula_count"],
            elapsed_sec=raw["elapsed_sec"],
            error=raw["error"],
            page_range=pr,
        )

    @staticmethod
    def _write_outputs(result: ParseResult, raw: dict, output_dir: Path) -> None:
        stem = result.source_path.stem
        if result.success:
            md_path = output_dir / f"{stem}.md"
            md_path.write_text(result.markdown, encoding="utf-8")
            logger.info("Wrote %s", md_path)

        meta_path = output_dir / f"{stem}.json"
        meta: dict = {
            "source": str(result.source_path),
            "engine": result.engine.value,
            "category": result.category.value,
            "page_count": result.page_count,
            "table_count": result.table_count,
            "formula_count": result.formula_count,
            "elapsed_sec": round(result.elapsed_sec, 2),
            "success": result.success,
            "error": result.error,
            "elements": raw.get("elements", []),
        }
        if result.page_range is not None:
            meta["page_range"] = str(result.page_range)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote %s", meta_path)

    @staticmethod
    def _write_report(report: ParseReport, output_dir: Path) -> None:
        summary = {
            "total_files": report.total_files,
            "success": report.success_count,
            "failed": report.fail_count,
            "total_elapsed_sec": round(report.total_elapsed_sec, 2),
            "files": [
                {
                    "name": r.source_path.name,
                    "engine": r.engine.value,
                    "category": r.category.value,
                    "pages": r.page_count,
                    "tables": r.table_count,
                    "formulas": r.formula_count,
                    "elapsed_sec": round(r.elapsed_sec, 2),
                    "success": r.success,
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        report_path = output_dir / "_report.json"
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Batch report → %s", report_path)
