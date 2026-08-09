"""Otter MCP stdio server — repository brain for external AI agents."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure monorepo root is importable when launched as a script.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_API = _ROOT / "apps" / "api"
if _API.is_dir() and str(_API) not in sys.path:
    sys.path.insert(0, str(_API))

from mcp.server.fastmcp import FastMCP

from packages.architecture import build_constitution, explain_why, guard_proposal
from packages.impact import change_radar, dependency_impact, impact_from_focus
from packages.planner import build_plan
from packages.verify import review_gate, verify_repository

from . import __version__
from .api_client import api_request
from .errors import OtterMcpError, as_tool_error
from .logging_util import tool_timer
from .repo_context import resolve_repo
from .understand import understand_repository

mcp = FastMCP(
    "otter",
    instructions=(
        "Otter is a repository brain and verification layer. "
        "Use otter_understand / otter_impact / otter_guard before coding, "
        "and otter_verify / otter_review_gate after changes. "
        "Writes require approval via otter_task_execute."
    ),
)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)[:24000]


def _run(name: str, repository_id: str | None, fn):
    try:
        with tool_timer(name, repository_id):
            return _json(fn())
    except Exception as error:  # noqa: BLE001
        return _json(as_tool_error(error))


# --- Brain tools ---


@mcp.tool(name="otter_understand")
def otter_understand(
    task: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    focus_path: str | None = None,
    symbols: str | None = None,
    depth: int = 2,
) -> str:
    """Give targeted repository context for a question/task (not a full dump)."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        sym = [s.strip() for s in (symbols or "").split(",") if s.strip()]
        return understand_repository(
            ctx.root,
            task,
            focus_path=focus_path,
            symbols=sym or None,
            depth=max(1, min(depth, 5)),
        )

    return _run("otter_understand", repository_id, work)


@mcp.tool(name="otter_impact")
def otter_impact(
    focus_path: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    symbols: str | None = None,
    depth: int = 3,
) -> str:
    """Blast radius for a proposed change to a file/path before editing."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        sym = [s.strip() for s in (symbols or "").split(",") if s.strip()]
        return impact_from_focus(
            ctx.root,
            focus_paths=[focus_path],
            symbols=sym or None,
            depth=max(1, min(depth, 6)),
        )

    return _run("otter_impact", repository_id, work)


@mcp.tool(name="otter_change_radar")
def otter_change_radar(
    request: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
) -> str:
    """Pre-implementation scope: likely files, risks, complexity."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        return change_radar(ctx.root, request)

    return _run("otter_change_radar", repository_id, work)


@mcp.tool(name="otter_dependency_impact")
def otter_dependency_impact(
    target: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    depth: int = 3,
) -> str:
    """What would break if a file, module, or dependency changed/removed."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        return dependency_impact(ctx.root, target=target, depth=max(1, min(depth, 6)))

    return _run("otter_dependency_impact", repository_id, work)


# --- Architecture ---


@mcp.tool(name="otter_guard")
def otter_guard(
    proposal: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    target_paths: str | None = None,
) -> str:
    """Check a proposed implementation against inferred repository architecture."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        paths = [p.strip() for p in (target_paths or "").split(",") if p.strip()]
        return guard_proposal(ctx.root, proposal=proposal, target_paths=paths or None)

    return _run("otter_guard", repository_id, work)


@mcp.tool(name="otter_why")
def otter_why(
    subject: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
) -> str:
    """Explain why a file/symbol exists using evidence (never fabricates history)."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        return explain_why(ctx.root, subject)

    return _run("otter_why", repository_id, work)


@mcp.tool(name="otter_memory")
def otter_memory(
    repository_id: str | None = None,
    query: str | None = None,
    add_note: str | None = None,
) -> str:
    """List or add engineering memory via the Otter API (requires OTTER_SESSION)."""

    def work():
        rid = repository_id
        if not rid:
            from .config import load_config

            rid = load_config().repository_id
        if not rid:
            raise OtterMcpError(
                "repository_id_required",
                "repository_id is required for memory.",
                "Pass repository_id from an imported Otter workspace.",
            )
        if add_note:
            title = add_note.strip().split("\n", 1)[0][:80] or "MCP note"
            if len(title) < 2:
                title = "MCP note"
            return api_request(
                "POST",
                f"/repositories/{rid}/memory",
                {"kind": "note", "title": title, "content": add_note[:5000]},
            )
        entries = api_request("GET", f"/repositories/{rid}/memory")
        if query and isinstance(entries, list):
            q = query.lower()
            entries = [e for e in entries if q in json.dumps(e, default=str).lower()]
        return {"entries": entries, "query": query}

    return _run("otter_memory", repository_id, work)


# --- Verification ---


@mcp.tool(name="otter_verify")
def otter_verify(
    repository_id: str | None = None,
    repo_root: str | None = None,
    proposal: str | None = None,
    focus_paths: str | None = None,
) -> str:
    """Independently verify the working tree with allowlisted checks + architecture."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        paths = [p.strip() for p in (focus_paths or "").split(",") if p.strip()]
        return verify_repository(ctx.root, proposal=proposal, focus_paths=paths or None)

    return _run("otter_verify", repository_id, work)


@mcp.tool(name="otter_review_gate")
def otter_review_gate(
    objective: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    proposal: str | None = None,
    focus_paths: str | None = None,
) -> str:
    """PASS / REVIEW / BLOCKED combining impact, architecture, and verification."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        paths = [p.strip() for p in (focus_paths or "").split(",") if p.strip()]
        return review_gate(
            ctx.root,
            objective=objective,
            proposal=proposal,
            focus_paths=paths or None,
        )

    return _run("otter_review_gate", repository_id, work)


# --- Tasks (approval preserved) ---


@mcp.tool(name="otter_task_create")
def otter_task_create(
    objective: str,
    repository_id: str,
    constraints: str | None = None,
) -> str:
    """Create a structured engineering task (plan only — does not modify files)."""

    def work():
        ctx = resolve_repo(repository_id)
        plan = build_plan(ctx.root, objective)
        radar = change_radar(ctx.root, objective)
        # Persist via API when session available; otherwise return local artifact.
        task: dict[str, Any]
        try:
            body: dict[str, Any] = {"request": objective}
            task = api_request("POST", f"/repositories/{repository_id}/code-tasks", body)
            if constraints and isinstance(task, dict):
                task = {**task, "constraints_local": constraints}
        except OtterMcpError as error:
            if error.code in {"api_session_required", "api_unreachable", "api_error"}:
                task = {
                    "id": None,
                    "status": "planned_local",
                    "persisted": False,
                    "note": error.message,
                }
            else:
                raise
        return {
            "task": task,
            "understanding": plan.get("summary"),
            "plan": plan,
            "affected_areas": radar.get("likely_files"),
            "risks": radar.get("risks"),
            "verification_strategy": radar.get("recommended_verification"),
            "writes": False,
        }

    return _run("otter_task_create", repository_id, work)


@mcp.tool(name="otter_task_status")
def otter_task_status(repository_id: str, task_id: str) -> str:
    """Return code-task state from the Otter API."""

    def work():
        tasks = api_request("GET", f"/repositories/{repository_id}/code-tasks")
        if isinstance(tasks, list):
            match = next((t for t in tasks if str(t.get("id")) == task_id), None)
            if not match:
                raise OtterMcpError("task_not_found", f"Task {task_id} not found.")
            return match
        return tasks

    return _run("otter_task_status", repository_id, work)


@mcp.tool(name="otter_task_validate")
def otter_task_validate(
    objective: str,
    repository_id: str | None = None,
    repo_root: str | None = None,
    proposal: str | None = None,
) -> str:
    """Validate work against objective using the review gate."""

    def work():
        ctx = resolve_repo(repository_id, repo_root)
        return review_gate(ctx.root, objective=objective, proposal=proposal)

    return _run("otter_task_validate", repository_id, work)


@mcp.tool(name="otter_task_execute")
def otter_task_execute(repository_id: str, task_id: str, action: str = "apply") -> str:
    """Apply an approved code-task. Without approval returns approval_required (no writes)."""

    def work():
        action_l = action.strip().lower()
        if action_l == "generate":
            return api_request("POST", f"/repositories/{repository_id}/code-tasks/{task_id}/generate")
        if action_l == "approve":
            return api_request("POST", f"/repositories/{repository_id}/code-tasks/{task_id}/approve")
        if action_l != "apply":
            raise OtterMcpError(
                "invalid_action",
                f"Unsupported action `{action}`. Use generate|approve|apply.",
            )
        # Inspect status first
        tasks = api_request("GET", f"/repositories/{repository_id}/code-tasks")
        match = None
        if isinstance(tasks, list):
            match = next((t for t in tasks if str(t.get("id")) == task_id), None)
        status = (match or {}).get("status")
        if status != "approved":
            return {
                "status": "approval_required",
                "current_status": status,
                "message": "Task is not approved. Call action=approve after human review, then apply.",
                "writes": False,
            }
        return api_request("POST", f"/repositories/{repository_id}/code-tasks/{task_id}/apply")

    return _run("otter_task_execute", repository_id, work)


# --- Resources ---


def _repo_for_resource() -> Path:
    return resolve_repo().root


@mcp.resource("otter://repo/overview")
def resource_overview() -> str:
    """High-level repository overview from retrieval + constitution."""
    root = _repo_for_resource()
    constitution = build_constitution(root)
    return _json(
        {
            "root": str(root),
            "tech_stack": constitution.get("tech_stack"),
            "architecture": constitution.get("architecture"),
            "preferred_patterns": constitution.get("preferred_patterns"),
        }
    )


@mcp.resource("otter://repo/architecture")
def resource_architecture() -> str:
    from packages.impact import build_import_graph

    root = _repo_for_resource()
    nodes, edges = build_import_graph(root)
    return _json(
        {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "sample_nodes": nodes[:40],
            "sample_edges": edges[:60],
        }
    )


@mcp.resource("otter://repo/constitution")
def resource_constitution() -> str:
    return _json(build_constitution(_repo_for_resource()))


@mcp.resource("otter://repo/health")
def resource_health() -> str:
    """Lightweight health signals from constitution evidence (no DB)."""
    c = build_constitution(_repo_for_resource())
    score = 70
    if c.get("evidence", {}).get("tests"):
        score += 10
    if c.get("architecture", {}).get("layers_detected"):
        score += 10
    if len(c.get("forbidden_patterns") or []) > 2:
        score -= 10
    return _json({"score": max(0, min(100, score)), "signals": c.get("evidence")})


@mcp.resource("otter://repo/dependencies")
def resource_dependencies() -> str:
    c = build_constitution(_repo_for_resource())
    return _json(c.get("dependency_conventions") or {})


@mcp.resource("otter://task/{task_id}")
def resource_task(task_id: str) -> str:
    """Code-task snapshot from the Otter API (requires OTTER_SESSION + repository id)."""

    def work():
        from .config import load_config

        rid = load_config().repository_id
        if not rid:
            raise OtterMcpError(
                "repository_id_required",
                "Set OTTER_REPOSITORY_ID to resolve otter://task resources.",
            )
        tasks = api_request("GET", f"/repositories/{rid}/code-tasks")
        if not isinstance(tasks, list):
            return tasks
        match = next((t for t in tasks if str(t.get("id")) == task_id), None)
        if not match:
            raise OtterMcpError("task_not_found", f"Task {task_id} not found.")
        return match

    return _run("resource_task", None, work)


@mcp.resource("otter://task/{task_id}/plan")
def resource_task_plan(task_id: str) -> str:
    def work():
        task = json.loads(resource_task(task_id))
        if task.get("error"):
            return task
        return {
            "task_id": task_id,
            "request": task.get("request"),
            "proposed_summary": task.get("proposed_summary"),
            "status": task.get("status"),
            "plan_id": task.get("plan_id"),
        }

    return _run("resource_task_plan", None, work)


@mcp.resource("otter://task/{task_id}/diff")
def resource_task_diff(task_id: str) -> str:
    def work():
        task = json.loads(resource_task(task_id))
        if task.get("error"):
            return task
        return {
            "task_id": task_id,
            "status": task.get("status"),
            "patch": task.get("proposed_patch") or task.get("patch") or "",
            "summary": task.get("proposed_summary"),
        }

    return _run("resource_task_diff", None, work)


@mcp.resource("otter://task/{task_id}/verification")
def resource_task_verification(task_id: str) -> str:
    def work():
        task = json.loads(resource_task(task_id))
        if task.get("error"):
            return task
        ctx = resolve_repo()
        return review_gate(
            ctx.root,
            objective=str(task.get("request") or "verify task"),
            proposal=str(task.get("proposed_summary") or ""),
        )

    return _run("resource_task_verification", None, work)


# --- Prompts ---


@mcp.prompt(name="otter-investigate")
def prompt_investigate() -> str:
    return (
        "Investigate the repository with Otter before editing. "
        "Call otter_understand, then otter_impact on key files, then otter_why if needed."
    )


@mcp.prompt(name="otter-plan")
def prompt_plan() -> str:
    return (
        "Plan a change with Otter: otter_change_radar for scope, otter_guard for conventions, "
        "otter_task_create to record the task. Do not write files until approved."
    )


@mcp.prompt(name="otter-review")
def prompt_review() -> str:
    return "Review current changes with otter_verify and otter_review_gate. Treat BLOCKED as merge-blocking."


@mcp.prompt(name="otter-debug")
def prompt_debug() -> str:
    return "Debug using otter_understand + otter_dependency_impact on the failing symbol/file, then otter_why."


@mcp.prompt(name="otter-security-review")
def prompt_security() -> str:
    return (
        "Security review: otter_change_radar for auth/session scope, otter_guard for auth bypass, "
        "otter_verify focusing on secret paths and auth files."
    )


@mcp.prompt(name="otter-architecture-review")
def prompt_architecture() -> str:
    return "Architecture review: read otter://repo/constitution, then otter_guard on the proposal, then otter_review_gate."


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
