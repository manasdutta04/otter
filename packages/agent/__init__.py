"""Otter AI Software Engineer agent core (API/Python first)."""

from packages.agent.context import build_context, context_excludes_irrelevant
from packages.agent.decompose import decompose_pagination_example, decompose_task
from packages.agent.model_adapt import budget_for_model
from packages.agent.orchestrate import begin_implement, prepare_engineering_run
from packages.agent.patch import edit_prompt_addon, prefer_targeted_files
from packages.agent.state_machine import (
    IllegalTransition,
    assert_can_apply,
    assert_can_generate,
    assert_can_implement,
    can_transition,
    transition,
)
from packages.agent.tools import ROLE_ALLOW, ToolPermissionError, ToolRegistry
from packages.agent.types import (
    AgentRun,
    Confidence,
    ContextBundle,
    EngineerState,
    ModelBudget,
    TaskGraph,
    TaskNode,
    TaskStatus,
    ToolKind,
    ToolSpec,
    WorkerResult,
    WorkerRole,
)
from packages.agent.workers import (
    run_debugger,
    run_explorer,
    run_planner,
    run_reviewer,
    run_tester,
)

__all__ = [
    "AgentRun",
    "Confidence",
    "ContextBundle",
    "EngineerState",
    "IllegalTransition",
    "ModelBudget",
    "ROLE_ALLOW",
    "TaskGraph",
    "TaskNode",
    "TaskStatus",
    "ToolKind",
    "ToolPermissionError",
    "ToolRegistry",
    "ToolSpec",
    "WorkerResult",
    "WorkerRole",
    "assert_can_apply",
    "assert_can_generate",
    "assert_can_implement",
    "begin_implement",
    "budget_for_model",
    "build_context",
    "can_transition",
    "context_excludes_irrelevant",
    "decompose_pagination_example",
    "decompose_task",
    "edit_prompt_addon",
    "prefer_targeted_files",
    "prepare_engineering_run",
    "run_debugger",
    "run_explorer",
    "run_planner",
    "run_reviewer",
    "run_tester",
    "transition",
]
