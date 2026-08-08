"""High-level sequential orchestration for an engineering request (pre-patch)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from packages.agent.context import build_context
from packages.agent.model_adapt import budget_for_model
from packages.agent.state_machine import IllegalTransition, assert_can_implement, transition
from packages.agent.types import AgentRun, EngineerState
from packages.agent.workers import (
    build_graph_from_plan,
    run_explorer,
    run_planner,
)


def new_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


def prepare_engineering_run(
    *,
    repository_id: str,
    request: str,
    repo_root: Path | str,
    model: str = "qwen2.5-coder:7b",
    intelligence: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    plan_id: str | None = None,
    code_task_id: str | None = None,
    git_status: str = "",
) -> AgentRun:
    """
    Run Understand → Investigate → Plan → Decompose → AwaitApproval (sequential, no parallel LLM).
    Does not apply writes. Human must approve before implement/generate.
    """
    budget = budget_for_model(model)
    run = AgentRun(
        id=new_run_id(),
        repository_id=repository_id,
        request=request,
        state=EngineerState.IDLE,
        model=model,
        budget=budget,
        plan_id=plan_id,
        code_task_id=code_task_id,
    )

    run.state = transition(run.state, EngineerState.UNDERSTAND)
    context = build_context(
        repo_root,
        request,
        intelligence=intelligence,
        plan=plan,
        model=model,
        budget=budget,
        git_status=git_status,
    )
    run.context = context

    run.state = transition(run.state, EngineerState.INVESTIGATE)
    explore = run_explorer(Path(repo_root), request, context)
    run.worker_results.append(explore)

    run.state = transition(run.state, EngineerState.PLAN)
    planner = run_planner(request, context, explore)
    run.worker_results.append(planner)

    run.state = transition(run.state, EngineerState.DECOMPOSE)
    graph = build_graph_from_plan(request, context, planner.data, max_subtasks=budget.max_subtasks)
    run.graph = graph

    run.state = transition(run.state, EngineerState.AWAIT_APPROVAL)
    return run


def begin_implement(run: AgentRun) -> AgentRun:
    """Transition into IMPLEMENT only from AWAIT_APPROVAL."""
    assert_can_implement(run.state)
    run.state = transition(run.state, EngineerState.IMPLEMENT)
    return run


__all__ = [
    "IllegalTransition",
    "begin_implement",
    "new_run_id",
    "prepare_engineering_run",
]
