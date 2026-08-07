"""Otter MCP server — stdio JSON-RPC bridge to the Otter API."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _load_otter_config() -> dict[str, str]:
    """Prefer env; fall back to ~/.otter/config.json from `otter login`."""
    api_url = os.getenv("OTTER_API_URL", "").rstrip("/")
    session = os.getenv("OTTER_SESSION", "")
    config_path = Path.home() / ".otter" / "config.json"
    if config_path.is_file():
        try:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
            if not api_url:
                api_url = str(parsed.get("apiUrl") or "").rstrip("/")
            if not session:
                session = str(parsed.get("session") or "")
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return {
        "api_url": api_url or "http://localhost:8000",
        "session": session,
    }


def api_call(path: str, payload: dict[str, Any] | None = None) -> Any:
    cfg = _load_otter_config()
    url = cfg["api_url"]
    session = cfg["session"]
    headers = {"Accept": "application/json"}
    if session:
        headers["Cookie"] = f"otter_session={session}"
        headers["X-Otter-Session"] = session
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{url}{path}", data=body, headers=headers, method="POST" if body is not None else "GET")
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read())


TOOLS = [
    {
        "name": "repository_intelligence",
        "description": "Get Otter intelligence for a repository",
        "inputSchema": {
            "type": "object",
            "properties": {"repository_id": {"type": "string"}},
            "required": ["repository_id"],
        },
    },
    {
        "name": "repository_chat",
        "description": "Ask grounded questions about repository code",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_id": {"type": "string"},
                "question": {"type": "string"},
            },
            "required": ["repository_id", "question"],
        },
    },
    {
        "name": "repository_plan",
        "description": "Generate an implementation plan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_id": {"type": "string"},
                "request": {"type": "string"},
            },
            "required": ["repository_id", "request"],
        },
    },
    {
        "name": "repository_review",
        "description": "Get code review findings for a repository",
        "inputSchema": {
            "type": "object",
            "properties": {"repository_id": {"type": "string"}},
            "required": ["repository_id"],
        },
    },
    {
        "name": "repository_health",
        "description": "Get repository health scores",
        "inputSchema": {
            "type": "object",
            "properties": {"repository_id": {"type": "string"}},
            "required": ["repository_id"],
        },
    },
    {
        "name": "repository_memory",
        "description": "List engineering memory entries for a repository",
        "inputSchema": {
            "type": "object",
            "properties": {"repository_id": {"type": "string"}},
            "required": ["repository_id"],
        },
    },
]


def handle(message: dict[str, Any]) -> dict[str, Any]:
    method = message.get("method")
    msg_id = message.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "otter", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = message.get("params") or {}
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        repo_id = args.get("repository_id")
        try:
            if tool_name == "repository_intelligence":
                res = api_call(f"/repositories/{repo_id}/intelligence")
            elif tool_name == "repository_chat":
                res = api_call(f"/repositories/{repo_id}/chat", {"question": args.get("question")})
            elif tool_name == "repository_plan":
                res = api_call(f"/repositories/{repo_id}/plans", {"request": args.get("request")})
            elif tool_name == "repository_review":
                res = api_call(f"/repositories/{repo_id}/review")
            elif tool_name == "repository_health":
                res = api_call(f"/repositories/{repo_id}/health")
            elif tool_name == "repository_memory":
                res = api_call(f"/repositories/{repo_id}/memory")
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool {tool_name} not found"},
                }
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(error)},
            }
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": json.dumps(res, default=str)}]},
        }

    if msg_id is None:
        return {"jsonrpc": "2.0", "result": {}}
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method {method} not found"}}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            print(json.dumps(handle(json.loads(line))), flush=True)
        except Exception as error:  # noqa: BLE001 — surface any protocol error to client
            print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": str(error)}}), flush=True)


if __name__ == "__main__":
    main()
