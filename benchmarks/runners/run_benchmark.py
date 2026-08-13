"""CLI: run the Otter engineering benchmark against local Ollama models."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import yaml  # noqa: E402

from benchmarks.runners.model_runner import MODELS, MODEL_A, probe_models  # noqa: E402
from benchmarks.runners.patch import run_patch  # noqa: E402
from benchmarks.runners.planning import run_planning  # noqa: E402
from benchmarks.runners.report import write_all  # noqa: E402
from benchmarks.runners.retrieval import run_retrieval  # noqa: E402

TASKS_DIR = REPO_ROOT / "benchmarks" / "tasks"
LOCK_PATH = REPO_ROOT / "benchmarks" / "fixtures" / "repos.lock.yaml"
CACHE_DIR = REPO_ROOT / "benchmarks" / "cache"
WORK_DIR = REPO_ROOT / "benchmarks" / "workspaces"
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_tasks() -> list[dict[str, Any]]:
    tasks = []
    for path in sorted(TASKS_DIR.glob("task-*.yaml")):
        data = load_yaml(path)
        if isinstance(data, dict) and data.get("id"):
            tasks.append(data)
    return tasks


def ensure_repos(lock: dict[str, Any]) -> dict[str, Any]:
    repos_meta = (lock.get("repos") or {})
    resolved: dict[str, Any] = {}
    for repo_id, spec in repos_meta.items():
        kind = spec.get("kind")
        if kind == "local":
            path = (REPO_ROOT / str(spec["path"])).resolve()
            resolved[repo_id] = {
                "id": repo_id,
                "ok": path.is_dir(),
                "path": str(path),
                "error": None if path.is_dir() else f"local path missing: {path}",
            }
            continue
        dest = CACHE_DIR / repo_id
        if dest.is_dir() and (dest / ".git").exists():
            resolved[repo_id] = {"id": repo_id, "ok": True, "path": str(dest), "error": None}
            continue
        url = spec.get("url")
        tag = spec.get("tag")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        import subprocess
        import shutil

        git = shutil.which("git")
        if not git:
            resolved[repo_id] = {"id": repo_id, "ok": False, "path": str(dest), "error": "git not on PATH"}
            continue
        cmd = [git, "clone", "--depth", "1"]
        if tag:
            cmd += ["--branch", str(tag)]
        cmd += [str(url), str(dest)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as error:
            resolved[repo_id] = {"id": repo_id, "ok": False, "path": str(dest), "error": str(error)}
            continue
        if result.returncode != 0:
            resolved[repo_id] = {
                "id": repo_id,
                "ok": False,
                "path": str(dest),
                "error": (result.stderr or result.stdout or "git clone failed")[:500],
            }
            continue
        resolved[repo_id] = {"id": repo_id, "ok": True, "path": str(dest), "error": None}
    return resolved


def dataset_summary(tasks: list[dict[str, Any]], repos: dict[str, Any]) -> dict[str, Any]:
    diffs = [str(t.get("difficulty") or "") for t in tasks]
    return {
        "repositories": sorted(repos.keys()),
        "repo_count": len(repos),
        "task_count": len(tasks),
        "easy": diffs.count("easy"),
        "medium": diffs.count("medium"),
        "hard": diffs.count("hard"),
        "locate": sum(1 for t in tasks if t.get("kind") == "locate"),
        "implement": sum(1 for t in tasks if t.get("kind") == "implement"),
        "version": "Otter Benchmark v0.5",
    }


def intelligence_from_plan_payload(plan_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_points": plan_row.get("intelligence_entry_points") or [],
        "tech_stack": [],
        "analysis": {},
    }


async def run_one_task(
    task: dict[str, Any],
    *,
    model: str,
    repos: dict[str, Any],
    skip_generate: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    repo_id = str(task.get("repository"))
    repo = repos.get(repo_id) or {}
    gold = task.get("gold") or {}
    gold_files = list(gold.get("relevant_files") or [])
    row: dict[str, Any] = {
        "id": task.get("id"),
        "kind": task.get("kind"),
        "repository": repo_id,
        "difficulty": task.get("difficulty"),
        "prompt": task.get("prompt"),
        "status": "ok",
        "model": model,
    }
    if not repo.get("ok"):
        row["status"] = "BLOCKED"
        row["blocked_stage"] = "infrastructure"
        row["error"] = repo.get("error") or f"repository {repo_id} unavailable"
        row["latency_s"] = time.perf_counter() - started
        return row

    root = Path(str(repo["path"]))
    row["retrieval"] = run_retrieval(root, str(task.get("prompt") or ""), gold_files)
    row["planning"] = run_planning(root, str(task.get("prompt") or ""), gold)

    if task.get("kind") != "implement" or skip_generate:
        row["latency_s"] = time.perf_counter() - started
        return row

    slug = model.replace(":", "-")
    work = WORK_DIR / slug / str(task.get("id"))
    plan = (row["planning"] or {}).get("plan") or {}
    intel = intelligence_from_plan_payload(row["planning"] or {})
    intel["ranked_files"] = list((row.get("retrieval") or {}).get("ranked_files") or [])
    row["patch"] = await run_patch(
        repo_root=root,
        work_root=work,
        task_id=str(task.get("id")),
        prompt=str(task.get("prompt") or ""),
        gold=gold,
        model=model,
        intelligence=intel,
        plan=plan,
        extra_paths=list(intel["ranked_files"]),
    )
    row["latency_s"] = time.perf_counter() - started
    return row


async def run_model(
    model: str,
    tasks: list[dict[str, Any]],
    *,
    repos: dict[str, Any],
    probe_entry: dict[str, Any],
    skip_generate: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "probe": probe_entry,
        "tasks": [],
    }
    if probe_entry.get("status") != "available":
        for task in tasks:
            payload["tasks"].append(
                {
                    "id": task.get("id"),
                    "kind": task.get("kind"),
                    "repository": task.get("repository"),
                    "difficulty": task.get("difficulty"),
                    "status": "BLOCKED",
                    "blocked_stage": "infrastructure",
                    "error": probe_entry.get("error") or "model unavailable",
                    "model": model,
                }
            )
        return payload
    for task in tasks:
        print(f"[{model}] {task.get('id')} {task.get('kind')} {task.get('repository')}", flush=True)
        row = await run_one_task(task, model=model, repos=repos, skip_generate=skip_generate)
        payload["tasks"].append(row)
        raw_path = RESULTS_DIR / "raw" / f"{model.replace(':', '-')}-{task.get('id')}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return payload


async def async_main(args: argparse.Namespace) -> int:
    lock = load_yaml(LOCK_PATH)
    tasks = load_tasks()
    if args.task:
        wanted = set(args.task)
        tasks = [t for t in tasks if t.get("id") in wanted]
    models = list(args.model) if args.model else list(MODELS)
    print("Probing Ollama…", flush=True)
    probe = probe_models(models)
    print(json.dumps({k: v.get("status") for k, v in (probe.get("models") or {}).items()}, indent=2), flush=True)
    print("Ensuring repositories…", flush=True)
    repos = ensure_repos(lock)
    for repo_id, info in repos.items():
        print(f"  {repo_id}: {'ok' if info.get('ok') else info.get('error')}", flush=True)
    dataset = dataset_summary(tasks, repos)
    all_results: dict[str, dict[str, Any]] = {}
    for model in models:
        entry = (probe.get("models") or {}).get(model) or {"status": "BLOCKED", "error": "not probed"}
        all_results[model] = await run_model(
            model,
            tasks,
            repos=repos,
            probe_entry=entry,
            skip_generate=args.skip_generate,
        )
    write_all(RESULTS_DIR, repo_root=REPO_ROOT, probe=probe, dataset=dataset, all_results=all_results)
    print(f"Wrote {RESULTS_DIR / 'report.md'}", flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Otter engineering benchmark")
    parser.add_argument("--model", action="append", help="Pin to one model (repeatable). Default: qwen2.5-coder:7b.")
    parser.add_argument("--task", action="append", help="Run only these task ids (repeatable).")
    parser.add_argument("--skip-generate", action="store_true", help="Skip LLM patch generation (retrieval+plan only).")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
