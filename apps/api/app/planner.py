import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryPlan

from packages.agent.context import is_source_rel


def _code_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if is_source_rel(rel):
            files.append(rel)
    return files


def _ranked_from_intelligence(intelligence: dict[str, object] | None) -> list[str]:
    hits: list[str] = []
    intel = intelligence or {}
    for key in ("ranked_files", "entry_points"):
        for item in intel.get(key) or []:
            rel = item if isinstance(item, str) else (item.get("rel_path") or item.get("path") or "")
            if rel and is_source_rel(str(rel)):
                hits.append(str(rel).replace("\\", "/"))
    return hits


def _ranked_from_retrieval(root: Path, request: str) -> list[str]:
    try:
        from packages.retrieval import RepositorySemanticIndex

        hits = []
        for hit in RepositorySemanticIndex(root).search(request, top_k=16):
            rel = str(hit.get("rel_path") or "").replace("\\", "/")
            if rel and is_source_rel(rel):
                hits.append(rel)
        return hits
    except Exception:  # noqa: BLE001
        return []


def build_plan(root: Path, request: str, intelligence: dict[str, object] | None) -> dict[str, object]:
    words = set(request.lower().replace("-", " ").split())
    files = _code_files(root)
    ranked = _ranked_from_intelligence(intelligence) or _ranked_from_retrieval(root, request)
    affected = []
    dependencies = []
    risks = []
    if {"auth", "oauth", "login", "authentication"} & words:
        affected = [file for file in files if any(term in file.lower() for term in ["auth", "user", "session", "login", "middleware", "route"])][:12]
        if not affected:
            affected = ranked[:12]
        dependencies = ["Identity provider configuration", "Session and authorization boundary", "Authentication and failure-path tests"]
        risks = ["Token handling and session invalidation", "Access control regressions", "Callback or redirect failures"]
    elif {"database", "schema", "migration", "postgres"} & words:
        affected = [file for file in files if any(term in file.lower() for term in ["model", "schema", "migration", "database", "repository"])][:12]
        if not affected:
            affected = ranked[:12]
        dependencies = ["Database migration", "Backward-compatible API contract", "Data backfill or rollback strategy"]
        risks = ["Existing data compatibility", "Partial migration failures", "Query performance"]
    elif {"api", "endpoint", "route"} & words:
        affected = [file for file in files if any(term in file.lower() for term in ["main", "route", "schema", "api"])][:12]
        if not affected:
            affected = ranked[:12]
        dependencies = ["Request and response contract", "Authentication and authorization", "API integration tests"]
        risks = ["Breaking existing clients", "Invalid input handling", "Error response consistency"]
    else:
        affected = ranked[:8] or files[:8]
        dependencies = ["Existing project conventions", "Automated tests", "Documentation update"]
        risks = ["Unidentified coupling", "Incomplete test coverage"]
    complexity = "high" if len(affected) > 8 or len(dependencies) > 2 else "medium" if affected else "low"
    title = "Plan: " + request.strip().rstrip(".")[:80]
    steps = ["Confirm the requested behavior against existing project conventions", f"Inspect and update the affected areas: {', '.join(affected[:5]) or 'repository entry points'}", "Implement the change with focused tests", "Run validation and review compatibility risks", "Document the decision and rollout notes"]
    return {"title": title, "complexity": complexity, "summary": f"This plan addresses: {request.strip()}. It begins with repository context, identifies affected surfaces, and ends with verification before implementation approval.", "steps": steps, "affected_files": affected, "dependencies": dependencies, "risks": risks}

async def save_plan(db: AsyncSession, repository_id: str, user_id: str, request: str, plan: dict[str, object]) -> RepositoryPlan:
    complexity = str(plan.get("complexity", "medium")).strip().lower()
    if complexity not in {"low", "medium", "high"}:
        complexity = "medium"
    record = RepositoryPlan(id=uuid4().hex[:12], repository_id=repository_id, user_id=user_id, request=request, title=str(plan["title"]), complexity=complexity, summary=str(plan["summary"]), steps=json.dumps(plan["steps"]), affected_files=json.dumps(plan["affected_files"]), dependencies=json.dumps(plan["dependencies"]), risks=json.dumps(plan["risks"]))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
