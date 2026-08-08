"""Task decomposition into a dependency-aware TaskGraph."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from packages.agent.types import Confidence, TaskGraph, TaskNode, WorkerRole


def _nid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def decompose_task(
    request: str,
    *,
    context_files: list[str] | None = None,
    max_subtasks: int = 8,
    plan: dict[str, Any] | None = None,
) -> TaskGraph:
    """
    Build a minimal, dependency-aware task graph.
    Deterministic heuristics first (works for small models); plan hints optional.
    """
    graph = TaskGraph()
    words = set(re.findall(r"[a-z0-9_]+", request.lower()))
    files = list(context_files or [])[:12]
    affected = list((plan or {}).get("affected_files") or files)[:12]

    explore = TaskNode(
        id=_nid("explore"),
        title="Explore relevant repository areas",
        description=f"Find code related to: {request[:120]}",
        role=WorkerRole.EXPLORER,
        allowed_files=affected,
        allowed_tools=["repo_tree", "search_code", "find_symbol", "read_file"],
        confidence=Confidence.MEDIUM,
        evidence=affected[:5],
    )
    graph.add(explore)

    plan_node = TaskNode(
        id=_nid("plan"),
        title="Plan implementation",
        description="Produce a focused plan with risks and verification",
        role=WorkerRole.PLANNER,
        depends_on=[explore.id],
        allowed_files=affected,
        allowed_tools=["read_file", "search_code", "find_symbol"],
    )
    graph.add(plan_node)

    impl_nodes: list[TaskNode] = []

    def add_impl(title: str, desc: str, deps: list[str]) -> TaskNode:
        node = TaskNode(
            id=_nid("impl"),
            title=title,
            description=desc,
            role=WorkerRole.IMPLEMENTER,
            depends_on=deps,
            allowed_files=affected,
            allowed_tools=["read_file", "search_code", "apply_edit", "create_file"],
        )
        graph.add(node)
        impl_nodes.append(node)
        return node

    if {"auth", "oauth", "login", "password", "session"} & words:
        m = add_impl("Update auth/session model if needed", "Inspect user/session model and auth service", [plan_node.id])
        s = add_impl("Modify auth service / routes", "Implement auth behavior change", [m.id])
        add_impl("Update auth-related UI or clients if present", "Login/callback surfaces", [s.id])
    elif {"pagination", "page", "limit", "offset", "cursor"} & words:
        m = add_impl("Add pagination to API layer", "Query params + response shape", [plan_node.id])
        add_impl("Wire callers/tests for pagination", "Update clients and tests", [m.id])
    elif {"test", "tests", "coverage"} & words and len(words) < 8:
        add_impl("Add or fix targeted tests", request[:200], [plan_node.id])
    elif {"endpoint", "route", "api"} & words:
        m = add_impl("Implement API endpoint", "Route + handler + validation", [plan_node.id])
        add_impl("Add endpoint tests", "Cover success and failure paths", [m.id])
    else:
        add_impl("Implement requested change", request[:240], [plan_node.id])

    # Cap implementers
    while len(impl_nodes) > max(1, max_subtasks - 3):
        removed = impl_nodes.pop()
        del graph.nodes[removed.id]

    test = TaskNode(
        id=_nid("test"),
        title="Validate changes",
        description="Run targeted tests / typecheck where available",
        role=WorkerRole.TESTER,
        depends_on=[n.id for n in impl_nodes],
        allowed_tools=["run_tests", "read_file", "git_diff"],
    )
    graph.add(test)

    review = TaskNode(
        id=_nid("review"),
        title="Review diff and requirement coverage",
        description="Check correctness, security, missing tests",
        role=WorkerRole.REVIEWER,
        depends_on=[test.id],
        allowed_tools=["read_file", "git_diff", "git_status"],
    )
    graph.add(review)

    # Ensure graph size bound
    if len(graph.nodes) > max_subtasks + 2:
        # keep explore, plan, one impl, test, review
        keep = {explore.id, plan_node.id, impl_nodes[0].id, test.id, review.id}
        graph.nodes = {k: v for k, v in graph.nodes.items() if k in keep}
        test.depends_on = [impl_nodes[0].id]
        review.depends_on = [test.id]

    return graph


def decompose_pagination_example() -> TaskGraph:
    """Fixture helper for tests."""
    return decompose_task("Add pagination to users API", context_files=["routes/users.ts", "tests/users.test.ts"])


__all__ = ["decompose_pagination_example", "decompose_task"]
