"""Tests for packages.agent — engineer core."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agent.context import build_context, context_excludes_irrelevant
from packages.agent.decompose import decompose_pagination_example, decompose_task
from packages.agent.model_adapt import budget_for_model
from packages.agent.patch import apply_edits_to_originals, prefer_targeted_files
from packages.agent.state_machine import (
    IllegalTransition,
    assert_can_apply,
    assert_can_generate,
    assert_can_implement,
    can_transition,
    transition,
)
from packages.agent.tools import ToolPermissionError, ToolRegistry
from packages.agent.types import EngineerState, TaskStatus, WorkerRole
from packages.agent.workers import run_explorer, run_planner


def test_decompose_pagination_has_sensible_subtasks():
    graph = decompose_pagination_example()
    titles = " ".join(n.title.lower() for n in graph.nodes.values())
    assert "pagination" in titles or "api" in titles
    assert any(n.role == WorkerRole.EXPLORER for n in graph.nodes.values())
    assert any(n.role == WorkerRole.TESTER for n in graph.nodes.values())
    assert any(n.role == WorkerRole.REVIEWER for n in graph.nodes.values())
    ready = graph.ready_nodes()
    assert ready
    assert all(n.status == TaskStatus.READY for n in ready)


def test_context_builder_excludes_irrelevant(tmp_path: Path):
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "login.ts").write_text("export function login() {}", encoding="utf-8")
    (tmp_path / "unrelated_billing_module.ts").write_text("export const x = 1", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"app"}', encoding="utf-8")
    bundle = build_context(tmp_path, "Fix login failing after password reset", model="qwen2.5-coder:7b")
    assert any("login" in f.path or "auth" in f.path for f in bundle.files)
    assert context_excludes_irrelevant(bundle, "unrelated_billing") or all(
        "billing" not in f.path for f in bundle.files if "package.json" not in f.path
    )
    assert bundle.char_count > 0
    assert len(bundle.files) <= 6


def test_worker_permissions_explorer_cannot_write(tmp_path: Path):
    (tmp_path / "a.ts").write_text(" const x = 1", encoding="utf-8")
    tools = ToolRegistry(tmp_path, allowed_files=["a.ts"])
    with pytest.raises(ToolPermissionError):
        tools.run(WorkerRole.EXPLORER, "apply_edit", {"path": "a.ts", "old_string": "1", "new_string": "2"})
    with pytest.raises(ToolPermissionError):
        tools.run(WorkerRole.PLANNER, "create_file", {"path": "b.ts", "content": "x"})
    with pytest.raises(ToolPermissionError):
        tools.run(WorkerRole.REVIEWER, "apply_patch_files", {"path": "a.ts", "content": "z"})


def test_implementer_scoped_files(tmp_path: Path):
    (tmp_path / "allowed.ts").write_text("const a = 1", encoding="utf-8")
    (tmp_path / "other.ts").write_text("const b = 1", encoding="utf-8")
    tools = ToolRegistry(tmp_path, allowed_files=["allowed.ts"])
    tools.run(
        WorkerRole.IMPLEMENTER,
        "apply_edit",
        {"path": "allowed.ts", "old_string": "1", "new_string": "2"},
    )
    with pytest.raises(ToolPermissionError):
        tools.run(
            WorkerRole.IMPLEMENTER,
            "apply_edit",
            {"path": "other.ts", "old_string": "1", "new_string": "2"},
        )


def test_state_machine_blocks_implement_before_approval():
    assert can_transition(EngineerState.IDLE, EngineerState.UNDERSTAND)
    state = transition(EngineerState.IDLE, EngineerState.UNDERSTAND)
    state = transition(state, EngineerState.INVESTIGATE)
    state = transition(state, EngineerState.PLAN)
    state = transition(state, EngineerState.DECOMPOSE)
    state = transition(state, EngineerState.AWAIT_APPROVAL)
    with pytest.raises(IllegalTransition):
        # cannot skip to apply from await without implement path via code task
        transition(EngineerState.IDLE, EngineerState.APPLY)
    assert_can_implement(state)
    with pytest.raises(IllegalTransition):
        assert_can_implement(EngineerState.UNDERSTAND)
    with pytest.raises(IllegalTransition):
        assert_can_generate("patch_ready")
    assert_can_generate("ready_for_approval")
    with pytest.raises(IllegalTransition):
        assert_can_apply("patch_ready")
    assert_can_apply("approved")


def test_model_adaptation_any_ollama_model():
    small = budget_for_model("qwen2.5-coder:3b")
    mid = budget_for_model("qwen2.5-coder:7b")
    large = budget_for_model("qwen2.5-coder:32b")
    gemma = budget_for_model("gemma4:e2b")
    assert small.tier == "small"
    assert small.max_context_files <= mid.max_context_files
    assert mid.tier == "medium"
    assert large.tier == "large"
    assert large.max_context_files >= mid.max_context_files
    assert gemma.tier == "small"
    # arbitrary model still works
    other = budget_for_model("my-custom-coder:latest")
    assert other.model == "my-custom-coder:latest"
    assert other.max_context_files >= 4


def test_targeted_edits_preferred():
    originals = {"a.ts": "const x = 1;\nconst y = 2;\n"}
    files = prefer_targeted_files(
        {
            "summary": "bump",
            "edits": [{"path": "a.ts", "old_string": "const x = 1;", "new_string": "const x = 42;"}],
        },
        originals,
    )
    assert files == [{"path": "a.ts", "content": "const x = 42;\nconst y = 2;\n"}]
    materialized = apply_edits_to_originals(
        [{"path": "a.ts", "old_string": "2", "new_string": "3"}],
        originals,
    )
    assert "const y = 3" in materialized[0]["content"]


def test_explorer_planner_smoke(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("export const main = 1", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    ctx = build_context(tmp_path, "Refactor main entrypoint", model="qwen2.5-coder:7b")
    explore = run_explorer(tmp_path, "Refactor main entrypoint", ctx)
    assert explore.ok
    plan = run_planner("Refactor main entrypoint", ctx, explore)
    assert plan.ok
    assert plan.data.get("affected_files")
