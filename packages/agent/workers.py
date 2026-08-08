"""Sequential mini-workers — roles with permissions; one LLM step at a time."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from packages.agent.decompose import decompose_task
from packages.agent.tools import ToolRegistry
from packages.agent.types import (
    Confidence,
    ContextBundle,
    TaskGraph,
    TaskNode,
    TaskStatus,
    WorkerResult,
    WorkerRole,
)


def run_explorer(root: Path, request: str, context: ContextBundle) -> WorkerResult:
    tools = ToolRegistry(root)
    tree = tools.run(WorkerRole.EXPLORER, "repo_tree", {"path": ".", "depth": 2})
    token = next((w for w in request.replace("-", " ").split() if len(w) > 2), "main")
    hits = tools.run(WorkerRole.EXPLORER, "search_code", {"query": token})
    evidence = list(context.evidence)[:8]
    return WorkerResult(
        role=WorkerRole.EXPLORER,
        ok=True,
        summary=f"Found {len(context.files)} relevant files for investigation",
        confidence=context.confidence,
        evidence=evidence,
        data={
            "tree_preview": tree[:1500],
            "search_preview": hits[:1500],
            "files": [f.path for f in context.files],
        },
    )


def run_planner(request: str, context: ContextBundle, explore: WorkerResult) -> WorkerResult:
    files = explore.data.get("files") or [f.path for f in context.files]
    return WorkerResult(
        role=WorkerRole.PLANNER,
        ok=True,
        summary=f"Plan for: {request[:100]}",
        confidence=Confidence.MEDIUM if files else Confidence.LOW,
        evidence=list(files)[:8],
        data={
            "steps": [
                "Inspect relevant files",
                "Apply minimal targeted changes",
                "Validate with tests",
                "Review diff before apply",
            ],
            "affected_files": files,
            "risks": ["Regressions in adjacent modules", "Missing tests"],
            "verification": ["run targeted tests", "inspect git diff"],
        },
    )


def build_graph_from_plan(
    request: str,
    context: ContextBundle,
    plan_data: dict[str, Any],
    max_subtasks: int = 8,
) -> TaskGraph:
    return decompose_task(
        request,
        context_files=list(plan_data.get("affected_files") or [f.path for f in context.files]),
        max_subtasks=max_subtasks,
        plan=plan_data,
    )


def run_implementer_prepare(node: TaskNode, context: ContextBundle) -> WorkerResult:
    allowed = node.allowed_files or [f.path for f in context.files]
    return WorkerResult(
        role=WorkerRole.IMPLEMENTER,
        ok=True,
        summary=f"Ready to implement: {node.title}",
        confidence=Confidence.MEDIUM,
        evidence=allowed[:8],
        data={"allowed_files": allowed, "task": node.description or node.title},
    )


def run_tester(root: Path, *, test_runner: Callable[[Path], Any] | None = None) -> WorkerResult:
    if test_runner is None:
        return WorkerResult(
            role=WorkerRole.TESTER,
            ok=True,
            summary="Tests deferred to API run_repository_tests after apply",
            confidence=Confidence.MEDIUM,
            evidence=[],
            data={"deferred": True},
        )
    result = test_runner(root)
    ok = bool(getattr(result, "ok", True)) if not isinstance(result, dict) else bool(result.get("ok", True))
    detail = str(getattr(result, "detail", result) if not isinstance(result, dict) else result)
    return WorkerResult(
        role=WorkerRole.TESTER,
        ok=ok,
        summary="Tests passed" if ok else "Tests failed",
        confidence=Confidence.HIGH if ok else Confidence.LOW,
        evidence=[],
        data={"result": detail[:4000]},
    )


def run_reviewer(context: ContextBundle, patch_files: list[dict[str, str]]) -> WorkerResult:
    paths = [p.get("path", "") for p in patch_files]
    return WorkerResult(
        role=WorkerRole.REVIEWER,
        ok=True,
        summary=f"Reviewed {len(paths)} changed file(s)",
        confidence=Confidence.MEDIUM,
        evidence=paths,
        data={
            "changed": paths,
            "checks": ["requirement coverage", "path safety", "prefer minimal diff"],
        },
    )


def run_debugger(failure_detail: str, context: ContextBundle) -> WorkerResult:
    return WorkerResult(
        role=WorkerRole.DEBUGGER,
        ok=True,
        summary="Investigate validation failure with focused context",
        confidence=Confidence.LOW,
        evidence=list(context.evidence)[:6],
        data={"failure": failure_detail[:2000], "next": "re-investigate then re-implement"},
    )


def mark_node(graph: TaskGraph, node_id: str, status: TaskStatus, result: dict[str, Any] | None = None) -> None:
    node = graph.nodes[node_id]
    node.status = status
    if result is not None:
        node.result = result


__all__ = [
    "build_graph_from_plan",
    "mark_node",
    "run_debugger",
    "run_explorer",
    "run_implementer_prepare",
    "run_planner",
    "run_reviewer",
    "run_tester",
]
