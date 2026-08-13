"""Run Otter's heuristic planner and score it deterministically."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.analyzer import inspect_repository
from app.planner import build_plan

from benchmarks.runners.metrics import score_plan


def list_repo_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", "__pycache__", ".venv", "dist"} for part in path.parts):
            continue
        files.append(path.relative_to(root).as_posix())
    return files


def run_planning(root: Path, prompt: str, gold: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        intelligence = inspect_repository(Path(root))
        plan = build_plan(Path(root), prompt, intelligence)
        existing = list_repo_files(root)
        rubric = score_plan(plan, gold, existing)
        return {
            "ok": True,
            "plan": {
                "title": plan.get("title"),
                "complexity": plan.get("complexity"),
                "summary": plan.get("summary"),
                "steps": plan.get("steps"),
                "affected_files": plan.get("affected_files"),
                "dependencies": plan.get("dependencies"),
                "risks": plan.get("risks"),
            },
            "intelligence_entry_points": list(intelligence.get("entry_points") or [])[:8],
            "rubric": rubric,
            "latency_s": time.perf_counter() - started,
            "error": None,
        }
    except Exception as error:  # noqa: BLE001
        return {
            "ok": False,
            "plan": {},
            "intelligence_entry_points": [],
            "rubric": {
                "A_files": 0,
                "B_approach": 0,
                "C_dependencies": 0,
                "D_verification": 0,
                "E_no_invented": 0,
                "total": 0,
                "max": 10,
                "score_pct": 0.0,
                "success": False,
            },
            "latency_s": time.perf_counter() - started,
            "error": str(error),
        }
