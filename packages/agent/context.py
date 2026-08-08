"""Bounded context builder — small focused context for local models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from packages.agent.model_adapt import budget_for_model
from packages.agent.types import Confidence, ContextBundle, ContextFile, ModelBudget

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".md"}
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt"}
SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 2}


def _score_path(rel: str, words: set[str], auth_boost: bool) -> float:
    score = 0.0
    low = rel.lower()
    for word in words:
        if word in low:
            score += 4.0
    if any(low.endswith(name) for name in ("main.py", "app.py", "index.ts", "server.ts", "route.ts", "routes.ts")):
        score += 2.0
    if auth_boost and any(
        term in low
        for term in ("auth", "login", "session", "passport", "next-auth", "password", "user", "middleware", "credential")
    ):
        score += 8.0
    return score


def _iter_code_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in CODE_SUFFIXES and path.name not in {"Dockerfile", "Makefile", *MANIFESTS}:
            continue
        out.append(path)
    return out


def build_context(
    repo_root: Path | str,
    task: str,
    *,
    intelligence: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    model: str = "qwen2.5-coder:7b",
    budget: ModelBudget | None = None,
    git_status: str = "",
    extra_paths: list[str] | None = None,
) -> ContextBundle:
    """
    Assemble a compact ContextBundle for the current engineering task.
    Deterministic scoring first; never dumps the whole repository.
    """
    root = Path(repo_root)
    budget = budget or budget_for_model(model)
    words = _words(task)
    auth_boost = bool(words & {"auth", "login", "password", "session", "oauth", "signup", "signin", "authentication", "credential"})

    scored: list[tuple[float, Path]] = []
    for path in _iter_code_files(root):
        rel = str(path.relative_to(root)).replace("\\", "/")
        scored.append((_score_path(rel, words, auth_boost), path))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[Path] = [p for s, p in scored if s > 0][: budget.max_context_files] or [
        p for _, p in scored[: budget.max_context_files]
    ]

    for hint in (plan or {}).get("affected_files") or []:
        candidate = root / str(hint)
        if candidate.is_file() and candidate not in selected:
            selected.insert(0, candidate)

    for name in MANIFESTS:
        extra = root / name
        if extra.exists() and extra not in selected:
            selected.insert(0, extra)

    if auth_boost:
        for preferred in (
            "shared/schema.ts",
            "server/db.ts",
            "server/routes.ts",
            "server/index.ts",
            "package.json",
        ):
            candidate = root / preferred
            if candidate.is_file() and candidate not in selected:
                selected.insert(0, candidate)

    for rel in extra_paths or []:
        candidate = root / rel
        if candidate.is_file() and candidate not in selected:
            selected.insert(0, candidate)

    files: list[ContextFile] = []
    evidence: list[str] = []
    for path in selected[: budget.max_context_files]:
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        content = raw if path.name.lower() in MANIFESTS else raw[: budget.max_chars_per_file]
        score = next((s for s, p in scored if p == path), 0.0)
        files.append(ContextFile(path=rel, content=content, score=score))
        evidence.append(rel)

    # Drop low-relevance files that would only bloat small models (keep manifests).
    if len(files) > 2:
        manifests = [f for f in files if Path(f.path).name.lower() in MANIFESTS]
        others = [f for f in files if Path(f.path).name.lower() not in MANIFESTS]
        others = [f for f in others if f.score > 0 or len(others) <= 2] or others[:2]
        files = (manifests + others)[: budget.max_context_files]

    entry_points = list((intelligence or {}).get("entry_points") or [])[:8]
    tech_stack = list((intelligence or {}).get("tech_stack") or [])[:12]
    routes: list[str] = []
    analysis = (intelligence or {}).get("analysis") or {}
    if isinstance(analysis, dict):
        for route in analysis.get("api_routes") or []:
            if isinstance(route, dict):
                routes.append(f"{route.get('method', '?')} {route.get('path', '')} ({route.get('file', '')})")
            else:
                routes.append(str(route))

    confidence = Confidence.HIGH if any(f.score >= 8 for f in files) else (
        Confidence.MEDIUM if any(f.score > 0 for f in files) else Confidence.LOW
    )

    char_count = sum(len(f.content) for f in files)
    return ContextBundle(
        task=task,
        files=files,
        symbols=[],
        routes=routes[:20],
        entry_points=entry_points,
        tech_stack=tech_stack,
        git_status=git_status[:2000],
        plan_summary=str((plan or {}).get("summary") or "")[:1500],
        constraints=[
            "Prefer targeted edits over full-file rewrites",
            "Do not invent files outside the repository layout",
            f"Context limited to {budget.max_context_files} files for model {budget.model}",
        ],
        evidence=evidence,
        confidence=confidence,
        char_count=char_count,
    )


def context_excludes_irrelevant(bundle: ContextBundle, irrelevant_substr: str) -> bool:
    """Test helper: True if no selected file path contains the substring."""
    needle = irrelevant_substr.lower()
    return all(needle not in f.path.lower() for f in bundle.files)


__all__ = ["build_context", "context_excludes_irrelevant"]
