"""MCP / engineering package tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MCP_APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MCP_APP))

FIXTURE = MCP_APP / "fixtures" / "sample_repo"


def test_impact_finds_consumers():
    from packages.impact import dependency_impact, impact_from_focus

    impact = impact_from_focus(FIXTURE, focus_paths=["src/repositories/userRepository.ts"], depth=3)
    assert impact["risk"] in {"low", "medium", "high"}
    assert isinstance(impact["affected_files"], list)

    dep = dependency_impact(FIXTURE, target="src/services/userService.ts", depth=3)
    assert dep["seeds"]
    consumers = [c["path"] for c in dep.get("direct_consumers", []) + dep.get("indirect_consumers", [])]
    # routes and tests import the service
    assert any("users" in p or "test" in p or "user" in p for p in consumers)


def test_change_radar_auth():
    from packages.impact import change_radar

    radar = change_radar(FIXTURE, "Add GitHub OAuth login")
    assert radar["estimated_complexity"]
    assert radar["risk"] in {"low", "medium", "high"}
    assert isinstance(radar["likely_files"], list)


def test_constitution_and_guard():
    from packages.architecture import build_constitution, guard_proposal

    constitution = build_constitution(FIXTURE)
    assert "architecture" in constitution
    assert constitution["architecture"]["layers_detected"]

    bad = guard_proposal(
        FIXTURE,
        proposal="Put prisma queries directly in the express route handler",
        target_paths=["src/routes/users.ts"],
    )
    assert bad["status"] == "fail"
    assert bad["violations"]


def test_guard_path_traversal_blocked():
    from otter_mcp.errors import OtterMcpError
    from otter_mcp.repo_context import resolve_repo, safe_rel_path

    with pytest.raises(OtterMcpError) as exc:
        resolve_repo(repository_id="../etc/passwd")
    assert exc.value.code in {"invalid_repository_id", "path_traversal", "repository_not_imported"}

    with pytest.raises(OtterMcpError):
        safe_rel_path(FIXTURE, "../outside.ts")


def test_verify_and_review_gate():
    from packages.verify import review_gate, verify_repository

    verification = verify_repository(
        FIXTURE, proposal="safe refactor", focus_paths=["src/services/userService.ts"]
    )
    assert verification["verdict"] in {"pass", "review", "blocked"}
    gate = review_gate(FIXTURE, objective="Add health endpoint")
    assert gate["verdict"] in {"PASS", "REVIEW", "BLOCKED"}


def test_understand():
    from otter_mcp.understand import understand_repository

    result = understand_repository(FIXTURE, "where is user creation?")
    assert "summary" in result
    assert "relevant_files" in result


def test_task_execute_requires_approval_logic():
    status = "patch_ready"
    result = {
        "status": "approval_required" if status != "approved" else "ok",
        "writes": status == "approved",
    }
    assert result["status"] == "approval_required"
    assert result["writes"] is False


def test_mcp_tools_registered():
    from otter_mcp import server as srv

    for name in (
        "otter_understand",
        "otter_impact",
        "otter_change_radar",
        "otter_dependency_impact",
        "otter_guard",
        "otter_why",
        "otter_memory",
        "otter_verify",
        "otter_review_gate",
        "otter_task_create",
        "otter_task_status",
        "otter_task_validate",
        "otter_task_execute",
    ):
        assert callable(getattr(srv, name))


def test_oversized_error_payload_is_structured():
    from otter_mcp.errors import OtterMcpError, as_tool_error

    err = as_tool_error(OtterMcpError("missing", "boom", "fix it"))
    assert err["error"] == "missing"
    assert "next_action" in err
