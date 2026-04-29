from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MarkdownQuality:
    structure_integrity: float
    table_fidelity: float
    paragraph_preservation: float


def evaluate_markdown_quality(markdown: str, plain_text: str) -> MarkdownQuality:
    md_lines = [l for l in markdown.splitlines() if l.strip()]
    txt_lines = [l for l in plain_text.splitlines() if l.strip()]

    heading_count = sum(1 for l in md_lines if l.strip().startswith("#"))
    structure_integrity = min(1.0, heading_count / max(1, len(md_lines) * 0.2))

    src_table_like = len(re.findall(r"\t|\|", plain_text))
    md_table_like = len(re.findall(r"\|", markdown))
    table_fidelity = 1.0 if src_table_like == 0 else min(1.0, md_table_like / src_table_like)

    preservation = min(1.0, len(md_lines) / max(1, len(txt_lines)))
    return MarkdownQuality(
        structure_integrity=round(structure_integrity, 3),
        table_fidelity=round(table_fidelity, 3),
        paragraph_preservation=round(preservation, 3),
    )
