"""Single-task generation harness for iterating on Qwen 7B without the full suite."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from benchmarks.runners.model_runner import MODEL_A  # noqa: E402
from benchmarks.runners.run_benchmark import (  # noqa: E402
    LOCK_PATH,
    RESULTS_DIR,
    ensure_repos,
    load_tasks,
    load_yaml,
    run_one_task,
)


async def async_main(args: argparse.Namespace) -> int:
    tasks = [task for task in load_tasks() if task.get("id") == args.task]
    if not tasks:
        print(f"unknown task: {args.task}", file=sys.stderr)
        return 2
    repos = ensure_repos(load_yaml(LOCK_PATH))
    row = await run_one_task(tasks[0], model=args.model, repos=repos, skip_generate=False)
    patch = row.get("patch") or {}
    out = {
        "task_id": row.get("id"),
        "model": args.model,
        "latency_s": row.get("latency_s"),
        "raw_completion_preview": patch.get("raw_completion_preview"),
        "summary": patch.get("summary"),
        "modified_files": patch.get("modified_files"),
        "schema_ok": bool(patch.get("generation_succeeded")),
        "quality_gate": patch.get("quality_gate") or patch.get("error"),
        "failure_category": patch.get("failure_category"),
        "e2e_success": patch.get("e2e_success"),
        "generate_latency_s": patch.get("generate_latency_s"),
        "first_attempt_latency_s": patch.get("first_attempt_latency_s"),
        "retry_latency_s": patch.get("retry_latency_s"),
        "context_files": patch.get("context_files"),
        "context_chars": patch.get("context_chars"),
        "error": patch.get("error") or row.get("error"),
    }
    dest = Path(args.out) if args.out else RESULTS_DIR / "raw" / f"harness-{args.model.replace(':', '-')}-{args.task}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"Wrote {dest}")
    return 0 if patch.get("generation_succeeded") else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Otter generate task against a local model")
    parser.add_argument("--task", required=True, help="Task id, e.g. task-012")
    parser.add_argument("--model", default=MODEL_A)
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
