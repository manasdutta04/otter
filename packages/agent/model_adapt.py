"""Model-aware budgets — adapt context/tools for small local Ollama models."""

from __future__ import annotations

import re

from packages.agent.types import ModelBudget


def _parse_size_hint(model: str) -> float | None:
    """Extract approximate parameter size in billions from model name if present."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*[bB]\b", model)
    if m:
        return float(m.group(1))
    m = re.search(r":(\d+)b\b", model.lower())
    if m:
        return float(m.group(1))
    # qwen2.5-coder:7b style already covered; e2b / tiny hints
    if "e2b" in model.lower() or "1b" in model.lower() or "3b" in model.lower():
        return 2.0
    return None


def budget_for_model(model: str) -> ModelBudget:
    """
    Any Ollama model is allowed. Budgets shrink for smaller models.
    Does not require Qwen; qwen2.5-coder:7b is the recommended baseline only.
    """
    name = (model or "").strip() or "qwen2.5-coder:7b"
    size = _parse_size_hint(name)
    lower = name.lower()

    if size is not None and size <= 4.5:
        return ModelBudget(
            model=name,
            max_context_files=4,
            max_chars_per_file=2000,
            max_tool_calls=6,
            max_worker_iterations=3,
            max_subtasks=5,
            prefer_targeted_edits=True,
            tier="small",
        )
    if size is not None and size <= 9:
        return ModelBudget(
            model=name,
            max_context_files=6,
            max_chars_per_file=3000,
            max_tool_calls=8,
            max_worker_iterations=4,
            max_subtasks=8,
            prefer_targeted_edits=True,
            tier="medium",
        )
    if size is not None and size >= 14:
        return ModelBudget(
            model=name,
            max_context_files=10,
            max_chars_per_file=5000,
            max_tool_calls=14,
            max_worker_iterations=8,
            max_subtasks=12,
            prefer_targeted_edits=True,
            tier="large",
        )

    # Unknown size: treat gemma tiny / mini as small; otherwise medium baseline
    if any(tok in lower for tok in ("mini", "tiny", "e2b", "gemma2:2b", "phi")):
        return budget_for_model(f"{name}:3b")

    return ModelBudget(model=name, tier="medium")


__all__ = ["budget_for_model"]
