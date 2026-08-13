"""Bounded context builder — small focused context for local models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from packages.agent.model_adapt import budget_for_model
from packages.agent.types import Confidence, ContextBundle, ContextFile, ModelBudget

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt"}
SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next", "docs", "_locale"}
JUNK_NAMES = {
    "license",
    "license.md",
    "license.txt",
    "authors",
    "makefile",
    "manifest.in",
    "contributing.md",
    "contributing.rst",
    "changelog.md",
    "changelog.rst",
    "funding.yml",
    "dependabot.yml",
}
JUNK_DIR_PARTS = {".github", "docs", "_locale", "lc_messages", "node_modules", ".git"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 2}


def is_source_rel(rel: str) -> bool:
    """True for implementation/test source, not licenses, locales, or CI metadata."""
    path = Path(str(rel).replace("\\", "/"))
    parts_l = {part.lower() for part in path.parts}
    if parts_l & JUNK_DIR_PARTS:
        return False
    if path.name.lower() in JUNK_NAMES:
        return False
    return path.suffix.lower() in CODE_SUFFIXES


def wants_manifest_context(task: str) -> bool:
    low = task.lower()
    return any(
        term in low
        for term in ("package.json", "dependency", "dependencies", "pyproject", "requirements", "manifest")
    )


def _usable_context_rel(rel: str, *, allow_manifest: bool) -> bool:
    name = Path(rel).name.lower()
    if name in MANIFESTS:
        return allow_manifest
    return is_source_rel(rel)


def _ordered_add(selected: list[str], seen: set[str], rel: str) -> None:
    norm = str(rel).replace("\\", "/").lstrip("./")
    if not norm or norm in seen:
        return
    seen.add(norm)
    selected.append(norm)


_ATTR_RE = re.compile(r"\b([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\b")
_SKIP_ATTR_MODS = {"e", "g", "i", "ie", "eg", "self", "this", "cls", "cls_", "super"}


def is_test_rel(rel: str) -> bool:
    path = str(rel).replace("\\", "/").lower()
    name = Path(path).name
    return (
        "/test/" in f"/{path}/"
        or "/tests/" in f"/{path}/"
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))
    )


def prompt_impl_path_hints(task: str, root: Path) -> list[str]:
    """Literal paths and module.attr → file guesses that exist on disk. Not task-id specific."""
    hints: list[str] = []
    try:
        from packages.retrieval import literal_paths_in_query

        hints.extend(literal_paths_in_query(task))
    except Exception:  # noqa: BLE001
        pass
    for match in _ATTR_RE.finditer(task or ""):
        mod = match.group(1)
        if mod.lower() in _SKIP_ATTR_MODS or len(mod) < 2:
            continue
        for candidate in (
            f"{mod}.py",
            f"src/{mod}.py",
            f"lib/{mod}.py",
            f"{mod}/__init__.py",
            f"src/{mod}/__init__.py",
        ):
            if (root / candidate).is_file():
                hints.append(candidate.replace("\\", "/"))
                break
    seen: set[str] = set()
    ordered: list[str] = []
    for rel in hints:
        norm = str(rel).replace("\\", "/").lstrip("./")
        if not norm or norm in seen:
            continue
        seen.add(norm)
        ordered.append(norm)
    return ordered


_STOP_IDENTS = {
    "the",
    "and",
    "for",
    "add",
    "with",
    "that",
    "this",
    "from",
    "should",
    "return",
    "class",
    "function",
    "file",
    "test",
    "unit",
    "small",
    "otherwise",
    "existing",
    "export",
    "import",
}


def focused_excerpt(content: str, task: str, max_chars: int) -> str:
    """Return a contiguous source window around task symbols, not a blind file prefix."""
    if max_chars <= 0 or len(content) <= max_chars:
        return content
    idents = [
        token
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", task or "")
        if token.lower() not in _STOP_IDENTS
    ]
    lines = content.splitlines(keepends=True)
    best_line: int | None = None
    for ident in idents:
        pattern = re.compile(rf"\b{re.escape(ident)}\b")
        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue
            if re.search(r"\b(def|class|function|const|export|async)\b", line):
                best_line = index
                break
        if best_line is not None:
            break
    if best_line is None:
        for ident in idents:
            found = content.find(ident)
            if found >= 0:
                start = max(0, found - min(240, max_chars // 4))
                return content[start : start + max_chars]
        return content[:max_chars]
    start_line = max(0, best_line - 6)
    chunk = "".join(lines[start_line:])
    return chunk[:max_chars]


def _finalize_generate_selection(
    selected: list[str],
    scores: dict[str, float],
    limit: int,
) -> list[str]:
    """Prefer implementation files plus at most one test inside the generate budget."""
    impls = [path for path in selected if not is_test_rel(path)]
    tests = [path for path in selected if is_test_rel(path)]
    impls.sort(key=lambda path: scores.get(path, 0.0), reverse=True)
    tests.sort(key=lambda path: scores.get(path, 0.0), reverse=True)
    if impls:
        keep_impl = impls[: max(1, limit - (1 if tests else 0))]
        ordered = keep_impl + tests[:1]
    else:
        ordered = tests[:limit]
    return ordered[:limit]


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
    Uses the same TF-IDF retriever as Otter search; never dumps the whole repository.
    """
    root = Path(repo_root)
    budget = budget or budget_for_model(model)
    allow_manifest = wants_manifest_context(task)
    selected: list[str] = []
    seen: set[str] = set()
    scores: dict[str, float] = {}

    def consider(rel: str, score: float = 0.0) -> None:
        norm = str(rel).replace("\\", "/").lstrip("./")
        if not norm:
            return
        candidate = root / norm
        if not candidate.is_file():
            return
        if not _usable_context_rel(norm, allow_manifest=allow_manifest):
            return
        scores[norm] = max(scores.get(norm, 0.0), score)
        _ordered_add(selected, seen, norm)

    for rel in prompt_impl_path_hints(task, root):
        consider(str(rel), score=80.0)

    for rel in extra_paths or []:
        consider(str(rel), score=50.0)

    intel = intelligence or {}
    for item in intel.get("ranked_files") or []:
        if isinstance(item, str):
            consider(item, score=45.0)
        elif isinstance(item, dict):
            consider(str(item.get("rel_path") or item.get("path") or ""), score=float(item.get("score") or 45.0))

    for rel in intel.get("entry_points") or []:
        consider(str(rel), score=20.0)

    try:
        from packages.retrieval import RepositorySemanticIndex

        hits = RepositorySemanticIndex(root).search(task, top_k=max(budget.max_context_files * 4, 16))
    except Exception:  # noqa: BLE001
        hits = []
    for hit in hits:
        consider(str(hit.get("rel_path") or ""), score=float(hit.get("score") or 1.0))

    for hint in (plan or {}).get("affected_files") or []:
        if is_source_rel(str(hint)):
            consider(str(hint), score=8.0)

    if allow_manifest:
        for name in MANIFESTS:
            if (root / name).is_file():
                consider(name, score=5.0)

    words = _words(task)
    auth_boost = bool(
        words & {"auth", "login", "password", "session", "oauth", "signup", "signin", "authentication", "credential"}
    )
    if auth_boost:
        for preferred in ("shared/schema.ts", "server/db.ts", "server/routes.ts", "server/index.ts"):
            consider(preferred, score=12.0)

    selected = _finalize_generate_selection(selected, scores, budget.max_context_files)

    files: list[ContextFile] = []
    evidence: list[str] = []
    for rel in selected:
        path = root / rel
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if path.name.lower() in MANIFESTS:
            content = raw
        else:
            content = focused_excerpt(raw, task, budget.max_chars_per_file)
        files.append(ContextFile(path=rel, content=content, score=scores.get(rel, 0.0)))
        evidence.append(rel)

    entry_points = list(intel.get("entry_points") or [])[:8]
    tech_stack = list(intel.get("tech_stack") or [])[:12]
    routes: list[str] = []
    analysis = intel.get("analysis") or {}
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
            "If a source file is in context, preserve its existing contents and apply a minimal edit",
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


__all__ = [
    "build_context",
    "context_excludes_irrelevant",
    "is_source_rel",
    "is_test_rel",
    "focused_excerpt",
    "prompt_impl_path_hints",
    "wants_manifest_context",
]
