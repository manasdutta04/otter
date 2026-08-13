"""Ollama probes and runner-only model pinning (no production edits)."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from contextlib import contextmanager
from collections.abc import Sequence
from typing import Any, Iterator

import httpx

MODEL_A = "qwen2.5-coder:7b"
MODEL_B = "gemma4:e2b"  # archived v0.1/v0.2 comparison only; not a live default
MODELS = (MODEL_A,)
OLLAMA_BASE = "http://127.0.0.1:11434"
OPENAI_BASE = f"{OLLAMA_BASE}/v1"
SLUGS = {
    MODEL_A: "qwen2.5-coder-7b",
    MODEL_B: "gemma4-e2b",
}


def ollama_list_names() -> tuple[list[str], str | None]:
    exe = shutil.which("ollama")
    if not exe:
        return [], "ollama executable not on PATH"
    try:
        result = subprocess.run(
            [exe, "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [], str(error)
    if result.returncode != 0:
        return [], (result.stderr or result.stdout or "ollama list failed")[:500]
    names: list[str] = []
    for line in (result.stdout or "").splitlines()[1:]:
        name = line.split()[0] if line.strip() else ""
        if name:
            names.append(name)
    return names, None


def tags_from_api() -> tuple[list[str], str | None]:
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(f"{OLLAMA_BASE}/api/tags")
        if response.status_code >= 400:
            return [], f"Ollama /api/tags HTTP {response.status_code}"
        names = []
        for item in (response.json() or {}).get("models") or []:
            name = item.get("name") or item.get("model")
            if name:
                names.append(str(name))
        return names, None
    except Exception as error:  # noqa: BLE001
        return [], str(error)


def ping_model(model: str) -> dict[str, Any]:
    started = time.perf_counter()
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 8,
        "messages": [
            {"role": "user", "content": "Reply with the single word pong."},
        ],
    }
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(f"{OPENAI_BASE}/chat/completions", json=payload)
        latency_s = time.perf_counter() - started
        if response.status_code >= 400:
            return {
                "ok": False,
                "latency_s": latency_s,
                "error": f"HTTP {response.status_code}: {(response.text or '')[:300]}",
                "usage": None,
            }
        data = response.json()
        message = ((data.get("choices") or [{}])[0].get("message") or {})
        content = message.get("content") or message.get("reasoning") or ""
        usage = data.get("usage")
        ok = response.status_code < 400
        return {
            "ok": ok,
            "latency_s": latency_s,
            "error": None if ok else "empty completion",
            "usage": usage if isinstance(usage, dict) else None,
            "preview": str(content)[:80],
        }
    except Exception as error:  # noqa: BLE001
        return {
            "ok": False,
            "latency_s": time.perf_counter() - started,
            "error": str(error),
            "usage": None,
        }


def probe_models(wanted: Sequence[str] | None = None) -> dict[str, Any]:
    wanted_models = list(wanted or MODELS)
    listed, list_error = ollama_list_names()
    tags, tags_error = tags_from_api()
    available = set(listed) | set(tags)
    models: dict[str, Any] = {}
    for model in wanted_models:
        present = model in available or any(name.startswith(model) for name in available)
        entry: dict[str, Any] = {
            "name": model,
            "available": bool(present),
            "status": "available" if present else "BLOCKED",
            "ping": None,
        }
        if present:
            ping = ping_model(model)
            entry["ping"] = ping
            if not ping.get("ok"):
                # Tag exists locally — still run tasks; ping failure is recorded, not a missing model.
                entry["error"] = ping.get("error")
        else:
            entry["error"] = "model tag not present in ollama list; not pulling"
        models[model] = entry
    return {
        "ollama_list": listed,
        "ollama_list_error": list_error,
        "api_tags": tags,
        "api_tags_error": tags_error,
        "models": models,
        "healthy": tags_error is None or bool(listed),
    }


@contextmanager
def pin_model(model: str, base_url: str = OPENAI_BASE) -> Iterator[None]:
    """Disable Ollama failover for one generate_patch call. Runner-only."""
    import app.llm as llm

    def _validate() -> tuple[str, str, str]:
        return "ollama", model, base_url

    def _candidates(primary: str, *, free_failover: bool) -> list[str]:
        return [model]

    original_validate = llm._validate_llm_settings
    original_candidates = llm._free_model_candidates
    llm._validate_llm_settings = _validate  # type: ignore[method-assign]
    llm._free_model_candidates = _candidates  # type: ignore[method-assign]
    try:
        yield
    finally:
        llm._validate_llm_settings = original_validate  # type: ignore[method-assign]
        llm._free_model_candidates = original_candidates  # type: ignore[method-assign]


def model_slug(model: str) -> str:
    return SLUGS.get(model, model.replace(":", "-").replace("/", "-"))
