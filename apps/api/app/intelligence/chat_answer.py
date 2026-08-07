"""Grounded chat answers: retrieve code, then explain it (LLM when available)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.llm import (
    _free_model_candidates,
    _is_ollama_base,
    _llm_headers,
    _resolve_base_url,
    _validate_llm_settings,
)

logger = logging.getLogger(__name__)


async def explain_retrieved_context(question: str, contexts: list[dict[str, Any]]) -> str:
    """Ask the configured LLM to explain the retrieved snippets. Raises on failure."""
    if not contexts:
        raise ValueError("No contexts to explain")
    key, model, base = _validate_llm_settings()
    blocks: list[str] = []
    total = 0
    for ctx in contexts[:5]:
        path = ctx.get("path") or "unknown"
        start = ctx.get("start_line")
        end = ctx.get("end_line")
        loc = f"{path}:L{start}-{end}" if start and end else str(path)
        body = str(ctx.get("content") or "")[:1800]
        block = f"### {loc}\n{body}"
        if total + len(block) > 7000:
            break
        blocks.append(block)
        total += len(block)
    context_blob = "\n\n".join(blocks)
    prompt = (
        "You are Otter, a senior engineer answering questions about ONE repository.\n"
        "Write a clear explanation in plain English (2–4 short paragraphs).\n"
        "Rules:\n"
        "- Answer WHAT happens and HOW it works, not only which file to open.\n"
        "- Use only the provided source excerpts; if something is missing, say what is unclear.\n"
        "- Mention the important files/symbols by name.\n"
        "- Do not invent APIs, libraries, or files that are not in the excerpts.\n"
        "- Do not return JSON or markdown fences.\n\n"
        f"Question: {question.strip()}\n\n"
        f"Source excerpts:\n{context_blob}"
    )
    candidates = _free_model_candidates(model, free_failover=True)
    local = _is_ollama_base(base)
    request_base = _resolve_base_url(base)
    last_error = "unknown"
    for model_id in candidates[:2]:
        payload: dict[str, object] = {
            "model": model_id,
            "temperature": 0.2,
            "max_tokens": 700,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Explain codebase behavior clearly for another engineer. "
                        "Prefer flow and mechanism over file-hunting."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if local:
            payload["options"] = {"num_ctx": 4096, "num_predict": 700}
        try:
            async with httpx.AsyncClient(timeout=120.0 if local else 60.0) as client:
                response = await client.post(
                    f"{request_base.rstrip('/')}/chat/completions",
                    headers=_llm_headers(key, base),
                    json=payload,
                )
            if response.status_code >= 400:
                last_error = f"{model_id} HTTP {response.status_code}"
                logger.warning("Chat explain %s failed: %s", model_id, last_error)
                continue
            content = str(response.json()["choices"][0]["message"]["content"] or "").strip()
            content = content.replace("```", "").strip()
            if len(content) < 40:
                last_error = f"{model_id}: empty explanation"
                continue
            return content[:4000]
        except Exception as error:  # noqa: BLE001
            last_error = f"{model_id}: {error}"
            logger.warning("Chat explain attempt failed: %s", last_error)
            continue
    raise ValueError(f"Chat explain failed: {last_error}")
