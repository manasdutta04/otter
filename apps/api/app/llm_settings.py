"""Deployment-wide LLM runtime settings (DB + shared file for API/worker)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import LlmRuntimeSettings

logger = logging.getLogger(__name__)

SINGLETON_ID = "default"
Provider = Literal["ollama", "openai_compatible"]


@dataclass
class LlmRuntime:
    provider: Provider
    base_url: str
    model: str
    api_key: str
    free_failover: bool
    configured: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        key = self.api_key or ""
        masked = ""
        if key and key != "ollama":
            masked = ("*" * max(0, len(key) - 4)) + key[-4:]
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "api_key_set": bool(key and key != "ollama"),
            "api_key_masked": masked,
            "free_failover": self.free_failover,
            "configured": self.configured,
        }


def _runtime_file_path() -> Path:
    root = Path(get_settings().repository_data_dir).resolve()
    return root / ".otter" / "llm_runtime.json"


def _defaults_from_env() -> LlmRuntime:
    settings = get_settings()
    base = (settings.llm_base_url or "").strip() or "http://127.0.0.1:11434/v1"
    provider: Provider = "ollama"
    lowered = base.lower()
    if not any(m in lowered for m in ("11434", "ollama", "localhost", "127.0.0.1", "host.docker.internal")):
        provider = "openai_compatible"
    return LlmRuntime(
        provider=provider,
        base_url=base,
        model=(settings.llm_model or "qwen2.5-coder:7b").strip(),
        api_key=(settings.llm_api_key or "").strip(),
        free_failover=bool(settings.llm_free_failover),
        configured=False,
    )


def write_runtime_file(runtime: LlmRuntime) -> None:
    path = _runtime_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": runtime.provider,
        "base_url": runtime.base_url,
        "model": runtime.model,
        "api_key": runtime.api_key,
        "free_failover": runtime.free_failover,
        "configured": runtime.configured,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_runtime_file() -> LlmRuntime | None:
    path = _runtime_file_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    provider = data.get("provider") or "ollama"
    if provider not in ("ollama", "openai_compatible"):
        provider = "ollama"
    return LlmRuntime(
        provider=provider,  # type: ignore[arg-type]
        base_url=str(data.get("base_url") or "").strip(),
        model=str(data.get("model") or "").strip(),
        api_key=str(data.get("api_key") or "").strip(),
        free_failover=bool(data.get("free_failover", True)),
        configured=bool(data.get("configured", False)),
    )


def get_effective_runtime_sync() -> LlmRuntime:
    """Sync path for llm.py / celery — file first, then env defaults."""
    cached = read_runtime_file()
    if cached and cached.base_url and cached.model:
        return cached
    return _defaults_from_env()


def _row_to_runtime(row: LlmRuntimeSettings) -> LlmRuntime:
    provider = row.provider if row.provider in ("ollama", "openai_compatible") else "ollama"
    return LlmRuntime(
        provider=provider,  # type: ignore[arg-type]
        base_url=(row.base_url or "").strip(),
        model=(row.model or "").strip(),
        api_key=(row.api_key or "").strip(),
        free_failover=bool(row.free_failover),
        configured=bool(row.configured),
    )


async def ensure_runtime_row(db: AsyncSession) -> LlmRuntime:
    row = await db.get(LlmRuntimeSettings, SINGLETON_ID)
    if row is None:
        defaults = _defaults_from_env()
        # Prefer Docker-friendly Ollama URL when env still says loopback inside compose.
        if defaults.provider == "ollama" and "127.0.0.1" in defaults.base_url:
            file_hint = read_runtime_file()
            if file_hint:
                defaults = file_hint
        row = LlmRuntimeSettings(
            id=SINGLETON_ID,
            provider=defaults.provider,
            base_url=defaults.base_url,
            model=defaults.model,
            api_key=defaults.api_key,
            free_failover=defaults.free_failover,
            configured=defaults.configured,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        write_runtime_file(_row_to_runtime(row))
    else:
        # Keep file in sync for workers
        write_runtime_file(_row_to_runtime(row))
    return _row_to_runtime(row)


async def get_runtime(db: AsyncSession) -> LlmRuntime:
    return await ensure_runtime_row(db)


async def save_runtime(
    db: AsyncSession,
    *,
    provider: Provider,
    base_url: str,
    model: str,
    api_key: str | None,
    free_failover: bool,
    keep_existing_key: bool = False,
) -> LlmRuntime:
    row = await db.get(LlmRuntimeSettings, SINGLETON_ID)
    if row is None:
        await ensure_runtime_row(db)
        row = await db.get(LlmRuntimeSettings, SINGLETON_ID)
    assert row is not None
    row.provider = provider
    row.base_url = base_url.strip().rstrip("/")
    if not row.base_url.endswith("/v1") and provider == "openai_compatible":
        # Allow either form; normalize bare hosts to /v1 for OpenAI clients
        if row.base_url and not row.base_url.endswith("/v1"):
            pass
    row.model = model.strip()
    if keep_existing_key and (api_key is None or api_key == ""):
        pass
    elif api_key is not None:
        row.api_key = api_key.strip()
    row.free_failover = free_failover
    row.configured = True
    await db.commit()
    await db.refresh(row)
    runtime = _row_to_runtime(row)
    write_runtime_file(runtime)
    return runtime


def _ollama_root(base_url: str) -> str:
    """Map OpenAI-compatible .../v1 to Ollama native root."""
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    return root.rstrip("/")


async def list_models(runtime: LlmRuntime) -> list[str]:
    from app.llm import _resolve_base_url

    base = _resolve_base_url(runtime.base_url)
    names: list[str] = []
    try:
        if runtime.provider == "ollama" or _is_likely_ollama(base):
            root = _ollama_root(base)
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(f"{root}/api/tags")
            if response.status_code < 400:
                for item in (response.json() or {}).get("models") or []:
                    name = item.get("name") or item.get("model")
                    if name:
                        names.append(str(name))
                return sorted(set(names))
        # OpenAI-compatible /v1/models
        headers = {}
        key = runtime.api_key or ("ollama" if _is_likely_ollama(base) else "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{base.rstrip('/')}/models", headers=headers)
        if response.status_code < 400:
            for item in (response.json() or {}).get("data") or []:
                mid = item.get("id")
                if mid:
                    names.append(str(mid))
    except Exception as error:  # noqa: BLE001
        logger.warning("list_models failed: %s", error)
    return sorted(set(names))


def _is_likely_ollama(base: str) -> bool:
    lowered = (base or "").lower()
    return any(m in lowered for m in ("11434", "ollama", "localhost", "127.0.0.1", "host.docker.internal"))


async def test_runtime(runtime: LlmRuntime) -> dict[str, Any]:
    from app.llm import _is_ollama_base, _llm_headers, _resolve_base_url

    base = _resolve_base_url(runtime.base_url)
    key = (runtime.api_key or "").strip()
    if not key and _is_ollama_base(base):
        key = "ollama"
    models = await list_models(runtime)
    reachable = False
    completion_ok = False
    detail = ""
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            # Cheap reachability
            if runtime.provider == "ollama" or _is_ollama_base(base):
                root = _ollama_root(base)
                ping = await client.get(f"{root}/api/tags")
                reachable = ping.status_code < 400
                if not reachable:
                    detail = f"Ollama tags HTTP {ping.status_code}"
            else:
                ping = await client.get(
                    f"{base.rstrip('/')}/models",
                    headers=_llm_headers(key, base),
                )
                reachable = ping.status_code < 400
                if not reachable:
                    detail = f"Models HTTP {ping.status_code}: {(ping.text or '')[:200]}"
            if reachable and runtime.model:
                payload = {
                    "model": runtime.model,
                    "temperature": 0,
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
                }
                if _is_ollama_base(base):
                    payload["options"] = {"num_ctx": 512, "num_predict": 16}
                comp = await client.post(
                    f"{base.rstrip('/')}/chat/completions",
                    headers=_llm_headers(key, base),
                    json=payload,
                )
                completion_ok = comp.status_code < 400
                if not completion_ok:
                    detail = f"Completion HTTP {comp.status_code}: {(comp.text or '')[:240]}"
                else:
                    detail = "Model responded"
    except Exception as error:  # noqa: BLE001
        detail = str(error)
        reachable = False
        completion_ok = False
    return {
        "ok": reachable and (completion_ok or not runtime.model),
        "reachable": reachable,
        "completion_ok": completion_ok,
        "models": models[:40],
        "model": runtime.model,
        "provider": runtime.provider,
        "base_url": runtime.base_url,
        "detail": detail,
    }
