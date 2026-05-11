"""Structured logging setup for OmniParser."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def setup_logging(level: str = "INFO", log_file: str = "omniparser.log") -> None:
    """Configure the root ``omniparser`` logger.

    Logs go to both stderr (via Rich for pretty terminal output) and a
    rotating file.

    Calling this function more than once is safe — subsequent calls are
    no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger("omniparser")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    console_handler = RichHandler(
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(logging.DEBUG)
    root.addHandler(console_handler)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
