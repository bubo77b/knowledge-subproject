from __future__ import annotations

import re


class MarkdownNormalizer:
    def normalize(self, markdown: str) -> str:
        lines = markdown.splitlines()
        fixed = self._fix_heading_jumps(lines)
        fixed = self._collapse_empty_lines(fixed)
        return "\n".join(fixed).strip() + "\n"

    def _fix_heading_jumps(self, lines: list[str]) -> list[str]:
        current_level = 1
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#"):
                out.append(line.rstrip())
                continue
            match = re.match(r"^(#+)\s*(.*)$", stripped)
            if not match:
                out.append(line.rstrip())
                continue
            level = len(match.group(1))
            title = match.group(2).strip()
            if level > current_level + 1:
                level = current_level + 1
            current_level = max(1, level)
            out.append(f"{'#' * current_level} {title}".rstrip())
        return out

    def _collapse_empty_lines(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        empty_count = 0
        for line in lines:
            if line.strip():
                empty_count = 0
                out.append(line.rstrip())
            else:
                empty_count += 1
                if empty_count <= 1:
                    out.append("")
        return out
