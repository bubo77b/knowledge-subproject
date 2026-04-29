from __future__ import annotations

import re
from collections import Counter


class ObsidianLinker:
    def __init__(self, synonym_map: dict[str, str], keyword_min_len: int = 4, keyword_top_k: int = 12):
        self.synonym_map = {k.lower(): v.lower() for k, v in synonym_map.items()}
        self.keyword_min_len = keyword_min_len
        self.keyword_top_k = keyword_top_k

    def extract_keywords(self, markdown: str) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", markdown.lower())
        filtered = [w for w in words if len(w) >= self.keyword_min_len]
        normalized = [self.synonym_map.get(w, w) for w in filtered]
        counts = Counter(normalized)
        return [w for w, _ in counts.most_common(self.keyword_top_k)]

    def inject_wikilinks(self, markdown: str, keywords: list[str]) -> tuple[str, list[str]]:
        used_links: list[str] = []
        out = markdown
        for kw in keywords:
            pattern = rf"\b({re.escape(kw)})\b"
            if re.search(pattern, out, flags=re.IGNORECASE):
                out = re.sub(pattern, r"[[\1]]", out, count=1, flags=re.IGNORECASE)
                used_links.append(kw)
        return out, used_links
