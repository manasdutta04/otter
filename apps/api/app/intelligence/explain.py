"""LLM explain-only layer over structured repository analysis."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.llm import (
    FREE_CODING_MODELS,
    _extract_json_object,
    _free_model_candidates,
    _is_ollama_base,
    _llm_headers,
    _resolve_base_url,
    _validate_llm_settings,
)

logger = logging.getLogger(__name__)

EXPLAIN_SCHEMA_HINT = (
    '{"summary":"2-4 sentence repo summary",'
    '"folder_explanations":{"server":"short role","shared":"short role"},'
    '"auth_explanation":"optional short auth flow",'
    '"api_explanation":"optional short API overview"}'
)

META_QUESTION_HINTS = (
    "explain this repo",
    "explain the repository",
    "what is this project",
    "architecture",
    "how does login",
    "how does auth",
    "how the auth",
    "auth managed",
    "authentication",
    "api flow",
    "database",
    "middleware",
    "overview",
    "summarize",
)


def is_meta_architecture_question(question: str) -> bool:
    q = question.lower().strip()
    return any(hint in q for hint in META_QUESTION_HINTS)


def compress_analysis(analysis: dict[str, Any], *, max_chars: int = 3500) -> dict[str, Any]:
    """Shrink analysis JSON for ~2k-token LLM prompts."""
    compact = {
        "summary_facts": (analysis.get("summary_facts") or [])[:8],
        "languages": (analysis.get("languages") or [])[:8],
        "frameworks": (analysis.get("frameworks") or [])[:10],
        "package_managers": (analysis.get("package_managers") or [])[:6],
        "entry_points": (analysis.get("entry_points") or [])[:12],
        "folders": (analysis.get("folders") or [])[:12],
        "api_routes": (analysis.get("api_routes") or [])[:15],
        "databases": (analysis.get("databases") or [])[:6],
        "auth": (analysis.get("auth") or [])[:6],
        "testing": (analysis.get("testing") or [])[:8],
        "docker": (analysis.get("docker") or [])[:6],
        "ci": (analysis.get("ci") or [])[:6],
        "architecture_signals": (analysis.get("architecture_signals") or [])[:10],
    }
    encoded = json.dumps(compact, separators=(",", ":"))
    if len(encoded) <= max_chars:
        return compact
    compact["api_routes"] = compact["api_routes"][:6]
    compact["folders"] = compact["folders"][:6]
    return compact


def _validate_explain_payload(data: dict[str, Any]) -> dict[str, Any]:
    summary = str(data.get("summary") or "").strip()
    if len(summary) < 20:
        raise ValueError("Explain payload missing usable summary")
    folder_explanations = data.get("folder_explanations") or {}
    if not isinstance(folder_explanations, dict):
        raise ValueError("folder_explanations must be an object")
    cleaned_folders = {str(k): str(v).strip() for k, v in folder_explanations.items() if str(v).strip()}
    return {
        "summary": summary[:1200],
        "folder_explanations": cleaned_folders,
        "auth_explanation": str(data.get("auth_explanation") or "").strip()[:800],
        "api_explanation": str(data.get("api_explanation") or "").strip()[:800],
    }


async def explain_analysis(
    analysis: dict[str, Any],
    *,
    question: str | None = None,
) -> dict[str, Any]:
    """Ask local LLM to explain structured findings. Raises ValueError on failure."""
    key, model, base = _validate_llm_settings()
    compact = compress_analysis(analysis)
    user_q = (question or "Write a concise engineering overview of this repository.").strip()
    prompt = (
        "You explain repository intelligence. Return ONLY valid JSON matching this schema:\n"
        f"{EXPLAIN_SCHEMA_HINT}\n"
        "Rules: base answers only on the provided analysis JSON; do not invent files; keep folders keys short.\n"
        f"Question: {user_q}\n"
        f"Analysis: {json.dumps(compact, separators=(',', ':'))}"
    )
    candidates = _free_model_candidates(model, free_failover=True)
    local = _is_ollama_base(base)
    request_base = _resolve_base_url(base)
    last_error = "unknown"
    for model_id in candidates[:2]:
        for attempt in range(2):
            payload: dict[str, object] = {
                "model": model_id,
                "temperature": 0,
                "max_tokens": 900,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior engineer. Return only compact JSON. Never markdown fences.",
                    },
                    {"role": "user", "content": prompt if attempt == 0 else prompt + "\nPrevious reply was invalid. Return JSON only."},
                ],
            }
            if local:
                payload["options"] = {"num_ctx": 4096, "num_predict": 900}
            try:
                async with httpx.AsyncClient(timeout=120.0 if local else 60.0) as client:
                    response = await client.post(
                        f"{request_base.rstrip('/')}/chat/completions",
                        headers=_llm_headers(key, base),
                        json=payload,
                    )
                if response.status_code >= 400:
                    last_error = f"{model_id} HTTP {response.status_code}"
                    logger.warning("Explain %s failed: %s", model_id, last_error)
                    break
                content = response.json()["choices"][0]["message"]["content"]
                parsed = _validate_explain_payload(_extract_json_object(content))
                return parsed
            except Exception as error:  # noqa: BLE001
                last_error = f"{model_id}: {error}"
                logger.warning("Explain attempt failed: %s", last_error)
                continue
    raise ValueError(f"Explain failed: {last_error}")


def merge_explanation_into_legacy(data: dict[str, object], explanation: dict[str, Any]) -> dict[str, object]:
    """Apply explain output onto inspect_repository legacy dict before save."""
    data = dict(data)
    data["summary"] = explanation.get("summary") or data.get("summary")
    analysis = dict(data.get("analysis") or {})  # type: ignore[arg-type]
    analysis["folder_explanations"] = explanation.get("folder_explanations") or {}
    if explanation.get("auth_explanation"):
        analysis["auth_explanation"] = explanation["auth_explanation"]
    if explanation.get("api_explanation"):
        analysis["api_explanation"] = explanation["api_explanation"]
    data["analysis"] = analysis
    # Enrich rich folders with explanations
    rich = data.get("folders_rich")
    if isinstance(rich, list):
        updated = []
        for item in rich:
            if isinstance(item, dict):
                row = dict(item)
                path = str(row.get("path") or "")
                if path in analysis["folder_explanations"]:
                    row["explanation"] = analysis["folder_explanations"][path]
                updated.append(row)
            else:
                updated.append(item)
        data["folders_rich"] = updated
    return data
