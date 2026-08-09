"""Safe logging to stderr (never stdout — MCP stdio)."""
from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Iterator

_logger = logging.getLogger("otter_mcp")
if not _logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


@contextmanager
def tool_timer(name: str, repository_id: str | None = None) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
        _logger.info(
            "tool=%s repo=%s duration_ms=%.1f status=ok",
            name,
            repository_id or "-",
            (time.perf_counter() - start) * 1000,
        )
    except Exception:
        _logger.exception(
            "tool=%s repo=%s duration_ms=%.1f status=error",
            name,
            repository_id or "-",
            (time.perf_counter() - start) * 1000,
        )
        raise
