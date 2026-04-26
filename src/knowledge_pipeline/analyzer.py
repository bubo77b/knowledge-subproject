from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from openai import OpenAI

from .config import AppConfig
from .models import EnrichedNote, ParsedArtifact


STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "are",
    "was",
    "you",
    "your",
    "have",
    "has",
    "will",
    "can",
    "into",
    "about",
    "在",
    "我们",
    "这个",
    "一个",
    "以及",
    "进行",
}


def build_knowledge_note(document: ParsedArtifact, config: AppConfig, note_id: str) -> EnrichedNote:
    text_for_analysis = document.plain_text
    ai_result = _analyze(text_for_analysis, document.title, config)
    chart_insights = _extract_chart_insights(document.markdown, config)

    summary = ai_result.get("summary", "").strip() or f"{document.title} 的核心内容摘要。"
    tags = _normalize_list(ai_result.get("tags"), fallback=["knowledge", "imported"])
    entities = _normalize_list(ai_result.get("entities"), fallback=[])
    key_points = _normalize_list(ai_result.get("key_points"), fallback=[])
    related_topics = _normalize_list(ai_result.get("related_topics"), fallback=tags[:])

    return EnrichedNote(
        note_id=note_id,
        title=document.title,
        source_path=document.source_path,
        parser_used=document.parser_used,
        summary=summary,
        tags=tags,
        entities=entities,
        key_points=key_points,
        related_topics=related_topics,
        markdown_body=document.markdown,
        chart_insights=chart_insights,
    )


def _analyze(text: str, title: str, config: AppConfig) -> dict[str, Any]:
    chunks = _chunk_text(
        text=text,
        chunk_size=config.ai_chunk_size_chars,
        overlap=config.ai_chunk_overlap_chars,
        max_chunks=config.ai_max_chunks,
    )
    if not chunks:
        chunks = [text[: config.max_chars_for_analysis]]

    if not config.llm_enabled or config.llm_provider == "none":
        return _analyze_with_rules("\n".join(chunks[:3]), title)
    try:
        partials = [_analyze_with_provider(chunk, f"{title} (chunk {idx + 1})", config) for idx, chunk in enumerate(chunks)]
        return _merge_partial_results(partials, title)
    except Exception:
        return _analyze_with_rules("\n".join(chunks[:3]), title)


def _analyze_with_provider(text: str, title: str, config: AppConfig) -> dict[str, Any]:
    if config.llm_provider == "openai" and not config.llm_api_key:
        return _analyze_with_rules(text, title)
    if config.llm_provider == "ollama" and not config.llm_base_url:
        return _analyze_with_rules(text, title)
    return _analyze_with_llm(text, title, config)


def _analyze_with_llm(text: str, title: str, config: AppConfig) -> dict[str, Any]:
    client = OpenAI(api_key=config.llm_api_key, base_url=config.llm_base_url)
    prompt = (
        "你是知识管理助手。请分析文档并返回 JSON，字段为："
        "summary(string), tags(string[]), entities(string[]), key_points(string[]), related_topics(string[])."
        "不要返回 markdown，不要返回额外字段。"
    )
    user_content = f"标题: {title}\n\n内容:\n{text}"
    response = client.chat.completions.create(
        model=config.llm_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return _safe_json(content)


def _analyze_with_rules(text: str, title: str) -> dict[str, Any]:
    tokens = re.findall(r"[A-Za-z\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff]{1,}", text.lower())
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
    common = [word for word, _ in Counter(tokens).most_common(8)]
    key_points = [line.strip() for line in text.splitlines() if len(line.strip()) > 20][:5]

    summary = key_points[0] if key_points else f"{title} 的文档内容已导入。"
    return {
        "summary": summary,
        "tags": common[:5] if common else ["knowledge", "imported"],
        "entities": common[5:8],
        "key_points": key_points,
        "related_topics": common[:5],
    }


def _safe_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _normalize_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip().replace("[[", "").replace("]]", "")
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result if result else fallback


def _extract_chart_insights(markdown: str, config: AppConfig) -> list[str]:
    if config.chart_extractor == "none":
        return []

    insights: list[str] = []
    lines = markdown.splitlines()
    table_lines = [line for line in lines if "|" in line and len(line) >= config.chart_min_chars]
    if table_lines:
        insights.append(f"Detected {len(table_lines)} table-like lines that may represent chart data.")

    figure_mentions = [line.strip() for line in lines if re.search(r"(figure|图表|chart)", line, re.I)]
    if figure_mentions:
        insights.append(f"Detected {len(figure_mentions)} chart/figure references in the document.")

    if config.chart_extractor in {"deplot", "unichart"} and (table_lines or figure_mentions):
        insights.append(
            f"Chart extractor '{config.chart_extractor}' is configured. Integrate region-level inference for higher accuracy."
        )
    return insights


def _chunk_text(text: str, chunk_size: int, overlap: int, max_chunks: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    step = max(200, chunk_size - overlap)
    while start < len(text) and len(chunks) < max_chunks:
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def _merge_partial_results(partials: list[dict[str, Any]], title: str) -> dict[str, Any]:
    summaries = [item.get("summary", "").strip() for item in partials if item.get("summary")]
    all_tags = _collect_unique_lists(partials, "tags")
    all_entities = _collect_unique_lists(partials, "entities")
    all_points = _collect_unique_lists(partials, "key_points")
    all_topics = _collect_unique_lists(partials, "related_topics")
    return {
        "summary": "；".join(summaries[:3]) if summaries else f"{title} 的文档内容已分段解析。",
        "tags": all_tags[:8],
        "entities": all_entities[:10],
        "key_points": all_points[:12],
        "related_topics": all_topics[:8],
    }


def _collect_unique_lists(partials: list[dict[str, Any]], key: str) -> list[str]:
    result: list[str] = []
    for partial in partials:
        values = partial.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned and cleaned not in result:
                    result.append(cleaned)
    return result

