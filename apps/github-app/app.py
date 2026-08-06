"""Otter GitHub App webhook boundary.

Verifies signatures, acknowledges events, and forwards pull_request /
push payloads to the Otter API for durable processing when configured.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Otter GitHub App", version="0.2.0")


def otter_api_url() -> str:
    return os.getenv("OTTER_API_URL", "http://localhost:8000").rstrip("/")


def forward_event(event: str, delivery: str | None, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort forward to the Otter API internal webhook sink."""
    token = os.getenv("OTTER_INTERNAL_TOKEN", "")
    body = json.dumps({"event": event, "delivery": delivery, "payload": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json", "X-Otter-Event": event}
    if token:
        headers["X-Otter-Internal-Token"] = token
    request = Request(f"{otter_api_url()}/internal/github-events", data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "otter-github-app"}


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret:
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not x_hub_signature_256 or not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = x_github_event or "unknown"
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    action = payload.get("action")
    handled = False
    forward_result = None

    if event in {"pull_request", "push", "installation", "installation_repositories", "ping"}:
        handled = True
        if event != "ping":
            forward_result = forward_event(event, x_github_delivery, payload)

    return {
        "status": "accepted",
        "event": event,
        "action": action,
        "delivery": x_github_delivery,
        "handled": handled,
        "forwarded": forward_result is not None,
    }
