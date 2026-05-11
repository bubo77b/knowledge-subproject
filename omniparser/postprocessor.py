"""Markdown post-processing and optional LLM-based semantic cleanup."""

from __future__ import annotations

import logging
import re

from omniparser.config import Settings

logger = logging.getLogger("omniparser.postprocessor")


class MarkdownPostProcessor:
    """Rule-based Markdown normalisation applied after every engine."""

    def process(self, md: str) -> str:
        """Apply all cleanup passes in order."""
        md = self._fix_heading_levels(md)
        md = self._fix_broken_lines(md)
        md = self._normalise_latex(md)
        md = self._normalise_tables(md)
        md = self._collapse_blank_lines(md)
        return md.strip() + "\n"

    # ------------------------------------------------------------------

    @staticmethod
    def _fix_heading_levels(md: str) -> str:
        """Ensure heading levels never jump more than one step."""
        lines = md.splitlines()
        prev_level = 0
        out: list[str] = []
        for line in lines:
            m = re.match(r"^(#{1,6})\s", line)
            if m:
                cur = len(m.group(1))
                if prev_level > 0 and cur > prev_level + 1:
                    cur = prev_level + 1
                    line = "#" * cur + line[len(m.group(1)):]
                prev_level = cur
            out.append(line)
        return "\n".join(out)

    @staticmethod
    def _fix_broken_lines(md: str) -> str:
        """Rejoin lines broken mid-sentence (no punctuation at end)."""
        lines = md.splitlines()
        merged: list[str] = []
        for line in lines:
            if (
                merged
                and merged[-1]
                and not merged[-1].rstrip().endswith((".", "!", "?", ":", "|", "-", "#"))
                and not line.startswith(("#", "|", "-", "*", ">", "$$", "```"))
                and line
                and not re.match(r"^\s*$", merged[-1])
            ):
                merged[-1] = merged[-1].rstrip() + " " + line.lstrip()
            else:
                merged.append(line)
        return "\n".join(merged)

    @staticmethod
    def _normalise_latex(md: str) -> str:
        r"""Ensure inline math uses ``$...$`` and display math uses ``$$...$$``."""
        md = re.sub(r"\\\\?\((.+?)\\\\?\)", r"$\1$", md)
        md = re.sub(r"\\\\?\[(.+?)\\\\?\]", r"$$\1$$", md, flags=re.DOTALL)
        return md

    @staticmethod
    def _normalise_tables(md: str) -> str:
        """Trim whitespace around pipe separators in Markdown tables."""
        def _clean_row(match: re.Match[str]) -> str:
            row = match.group(0)
            parts = row.split("|")
            cells = [c.strip() for c in parts[1:-1]]
            return "| " + " | ".join(cells) + " |"

        return re.sub(r"^\|.*\|$", _clean_row, md, flags=re.MULTILINE)

    @staticmethod
    def _collapse_blank_lines(md: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", md)


# ------------------------------------------------------------------
# LLM-based semantic cleanup (optional)
# ------------------------------------------------------------------

class LLMPostProcessor:
    """Call a local LLM (via OpenAI-compatible API) for semantic fixes.

    This is intentionally kept thin — the LLM is only asked to fix
    heading hierarchy and broken sentences, not to rewrite content.
    """

    _SYSTEM_PROMPT = (
        "You are a Markdown formatting assistant. "
        "Fix heading hierarchy (h1→h2→h3 without gaps), "
        "rejoin sentences broken mid-word, and remove OCR artefacts. "
        "Do NOT rewrite, summarise, or add any new content. "
        "Return only the corrected Markdown."
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def process(self, md: str) -> str:
        if not self._settings.llm_enabled:
            return md

        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=self._settings.llm_base_url,
                api_key=self._settings.llm_api_key,
            )

            chunks = self._split_chunks(md, max_chars=6000)
            cleaned_parts: list[str] = []

            for chunk in chunks:
                resp = client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=[
                        {"role": "system", "content": self._SYSTEM_PROMPT},
                        {"role": "user", "content": chunk},
                    ],
                    temperature=0.0,
                    max_tokens=4096,
                )
                cleaned_parts.append(resp.choices[0].message.content or chunk)

            result = "\n\n".join(cleaned_parts)
            logger.info("LLM post-processing applied (%d chunks)", len(chunks))
            return result

        except Exception as exc:
            logger.warning("LLM post-processing failed, returning original: %s", exc)
            return md

    @staticmethod
    def _split_chunks(text: str, max_chars: int = 6000) -> list[str]:
        """Split text into chunks at paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) > max_chars and current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(para)
            current_len += len(para) + 2

        if current:
            chunks.append("\n\n".join(current))
        return chunks
