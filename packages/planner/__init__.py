"""AI Planner package for engineering task decomposition."""
from pathlib import Path


def build_plan(repo_root: Path, request: str, intelligence: dict | None = None) -> dict:
    """Generate a structured, repository-aware execution plan for a given task request."""
    words = set(request.lower().replace("-", " ").split())
    files = [
        str(path.relative_to(repo_root)).replace("\\", "/")
        for path in Path(repo_root).rglob("*")
        if path.is_file() and ".git" not in path.parts
    ]
    if {"auth", "oauth", "login", "authentication", "password"} & words:
        affected = [
            file
            for file in files
            if any(term in file.lower() for term in ["auth", "user", "session", "login", "middleware", "route", "password"])
        ][:12]
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
        ][:12]
        dependencies = ["Database migration", "Backward-compatible API contract", "Data backfill or rollback strategy"]
        risks = ["Existing data compatibility", "Partial migration failures", "Query performance"]
    elif {"api", "endpoint", "route", "health"} & words:
        affected = [
            file for file in files if any(term in file.lower() for term in ["main", "route", "schema", "api", "server"])
        ][:12]
        dependencies = ["Request and response contract", "Authentication and authorization", "API integration tests"]
        risks = ["Breaking existing clients", "Invalid input handling", "Error response consistency"]
    else:
        affected = list((intelligence or {}).get("entry_points", []) or [])[:8] or files[:8]
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
