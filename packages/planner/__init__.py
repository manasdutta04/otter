"""AI Planner package for engineering task decomposition."""
from pathlib import Path

from packages.agent.context import is_source_rel


def _code_files(repo_root: Path) -> list[str]:
    files: list[str] = []
    for path in Path(repo_root).rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if is_source_rel(rel):
            files.append(rel)
    return files


def _ranked(intelligence: dict | None, repo_root: Path, request: str) -> list[str]:
    hits: list[str] = []
    intel = intelligence or {}
    for key in ("ranked_files", "entry_points"):
        for item in intel.get(key) or []:
            rel = item if isinstance(item, str) else (item.get("rel_path") or item.get("path") or "")
            if rel and is_source_rel(str(rel)):
                hits.append(str(rel).replace("\\", "/"))
    if hits:
        return hits
    try:
        from packages.retrieval import RepositorySemanticIndex

        for hit in RepositorySemanticIndex(repo_root).search(request, top_k=16):
            rel = str(hit.get("rel_path") or "").replace("\\", "/")
            if rel and is_source_rel(rel):
                hits.append(rel)
    except Exception:  # noqa: BLE001
        return hits
    return hits


def build_plan(repo_root: Path, request: str, intelligence: dict | None = None) -> dict:
    """Generate a structured, repository-aware execution plan for a given task request."""
    words = set(request.lower().replace("-", " ").split())
    files = _code_files(repo_root)
    ranked = _ranked(intelligence, Path(repo_root), request)
    if {"auth", "oauth", "login", "authentication", "password"} & words:
        affected = [
            file
            for file in files
            if any(term in file.lower() for term in ["auth", "user", "session", "login", "middleware", "route", "password"])
        ][:12] or ranked[:12]
        dependencies = [
            "Identity provider configuration",
            "Session and authorization boundary",
            "Authentication and failure-path tests",
        ]
        risks = ["Token handling and session invalidation", "Access control regressions", "Callback or redirect failures"]
    elif {"database", "schema", "migration", "postgres"} & words:
        affected = [
            file
            for file in files
            if any(term in file.lower() for term in ["model", "schema", "migration", "database", "repository"])
        ][:12] or ranked[:12]
        dependencies = ["Database migration", "Backward-compatible API contract", "Data backfill or rollback strategy"]
        risks = ["Existing data compatibility", "Partial migration failures", "Query performance"]
    elif {"api", "endpoint", "route", "health"} & words:
        affected = [
            file for file in files if any(term in file.lower() for term in ["main", "route", "schema", "api", "server"])
        ][:12] or ranked[:12]
        dependencies = ["Request and response contract", "Authentication and authorization", "API integration tests"]
        risks = ["Breaking existing clients", "Invalid input handling", "Error response consistency"]
    else:
        affected = ranked[:8] or files[:8]
        dependencies = ["Existing project conventions", "Automated tests", "Documentation update"]
        risks = ["Unidentified coupling", "Incomplete test coverage"]

    complexity = "high" if len(affected) > 8 or len(dependencies) > 2 else "medium" if affected else "low"
    title = "Plan: " + request.strip().rstrip(".")[:80]
    steps = [
        "Confirm the requested behavior against existing project conventions",
        f"Inspect and update the affected areas: {', '.join(affected[:5]) or 'repository entry points'}",
        "Implement the change with focused tests",
        "Run validation and review compatibility risks",
        "Document the decision and rollout notes",
    ]
    return {
        "title": title,
        "complexity": complexity,
        "summary": (
            f"This plan addresses: {request.strip()}. It begins with repository context, "
            "identifies affected surfaces, and ends with verification before implementation approval."
        ),
        "steps": steps,
        "affected_files": affected,
        "dependencies": dependencies,
        "risks": risks,
    }


__all__ = ["build_plan"]
