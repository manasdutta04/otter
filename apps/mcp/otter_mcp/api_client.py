"""Optional HTTP client for Otter API persistence (memory, code-tasks)."""
from __future__ import annotations

from typing import Any

import httpx

from .config import load_config
from .errors import OtterMcpError


def api_request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    cfg = load_config()
    if not cfg.session:
        raise OtterMcpError(
            "api_session_required",
            "OTTER_SESSION is not set. CLI GitHub login alone is not an API session.",
            "Log into Otter Web/Docker and export the otter_session cookie as OTTER_SESSION.",
        )
    headers = {
        "Accept": "application/json",
        "Cookie": f"otter_session={cfg.session}",
        "X-Otter-Session": cfg.session,
    }
    url = f"{cfg.api_url}{path}"
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.request(method, url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise OtterMcpError(
                    "api_error",
                    f"API {method} {path} failed ({response.status_code}): {response.text[:500]}",
                    "Check OTTER_API_URL, session validity, and repository_id.",
                )
            if not response.content:
                return {}
            return response.json()
    except httpx.HTTPError as error:
        raise OtterMcpError(
            "api_unreachable",
            f"Could not reach Otter API at {cfg.api_url}: {error}",
            "Start the Otter Docker/API stack or correct OTTER_API_URL.",
        ) from error
