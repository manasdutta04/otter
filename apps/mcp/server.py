"""Backward-compatible entrypoint — prefer `python -m otter_mcp`."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_MCP = Path(__file__).resolve().parent
if str(_MCP) not in sys.path:
    sys.path.insert(0, str(_MCP))

from otter_mcp.server import main

if __name__ == "__main__":
    main()
