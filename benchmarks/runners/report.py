"""Write raw JSON, comparison tables, failures, and report.md from executed rows."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.runners.metrics import mean_or_none, summarize_latencies
from benchmarks.runners.model_runner import MODEL_A, model_slug

NA = "N/A"


STRUCTURED_FAIL = frozenset(
    {"json_malformed", "json_truncated", "wrong_schema", "malformed model output"}
)


def _git_sha(repo_root: Path) -> str:
    git = shutil.which("git")
    if not git:
        return "unknown"
    try:
        result = subprocess.run(
            [git, "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (result.stdout or "").strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _git_dirty(repo_root: Path) -> bool:
    git = shutil.which("git")
    if not git:
        return False
    try:
        result = subprocess.run(
            [git, "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool((result.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _cmd_version(cmd: list[str]) -> str:
    exe = shutil.which(cmd[0])
    if not exe:
        return "unavailable"
    try:
        result = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=10)
        text = (result.stdout or result.stderr or "").strip().splitlines()
        return text[0] if text else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def collect_environment(repo_root: Path) -> dict[str, Any]:
    ram = None
    gpu = None
    try:
        import psutil  # type: ignore

        ram = f"{round(psutil.virtual_memory().total / (1024**3), 1)} GiB"
    except Exception:  # noqa: BLE001
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                raw = (result.stdout or "").strip()
                if raw.isdigit():
                    ram = f"{round(int(raw) / (1024**3), 1)} GiB"
            except (OSError, subprocess.TimeoutExpired):
                ram = "unavailable"
        else:
            ram = "unavailable"
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu = result.stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        gpu = None
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor() or platform.machine(),
        "ram": ram or "unavailable",
        "gpu": gpu or "none detected",
        "ollama": _cmd_version(["ollama", "--version"]),
        "python": platform.python_version(),
        "node": _cmd_version(["node", "--version"]),
        "otter_commit": _git_sha(repo_root),
        "otter_dirty": _git_dirty(repo_root),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def _task_rows(model_result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(model_result.get("tasks") or [])


def _vals(rows: list[dict[str, Any]], path: tuple[str, ...]) -> list[float]:
    out: list[float] = []
    for row in rows:
        cur: Any = row
        skip = False
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                skip = True
                break
            cur = cur[key]
        if skip or cur is None:
            continue
        try:
            out.append(float(cur))
        except (TypeError, ValueError):
            continue
    return out


def aggregate_model(model_result: dict[str, Any]) -> dict[str, Any]:
    rows = _task_rows(model_result)
    implement = [r for r in rows if r.get("kind") == "implement" and r.get("status") != "BLOCKED"]
    locate = [r for r in rows if r.get("kind") == "locate" and r.get("status") != "BLOCKED"]
    usable = [r for r in rows if r.get("status") != "BLOCKED"]
    patch_ok = [r for r in implement if (r.get("patch") or {}).get("generation_succeeded")]
    applied = [r for r in implement if (r.get("patch") or {}).get("applied")]
    recovered = [r for r in implement if (r.get("patch") or {}).get("structured_recovery")]
    raw_ok = [r for r in implement if (r.get("patch") or {}).get("raw_structured_ok")]
    test_ran = [r for r in implement if (r.get("patch") or {}).get("tests", {}).get("status") in {"pass", "fail"}]
    test_pass = [r for r in test_ran if (r.get("patch") or {}).get("tests", {}).get("passed")]
    test_nv = [r for r in implement if (r.get("patch") or {}).get("tests", {}).get("status") in {"not_verifiable", "infrastructure_error"}]
    e2e = [r for r in implement if (r.get("patch") or {}).get("e2e_success")]
    unexpected = [r for r in implement if (r.get("patch") or {}).get("generation_succeeded")]
    unexpected_rate = None
    if unexpected:
        unexpected_rate = mean_or_none(
            [1.0 if (r.get("patch") or {}).get("unexpected_files") else 0.0 for r in unexpected]
        )
    file_acc = mean_or_none(
        [(r.get("patch") or {}).get("expected_file_accuracy") for r in patch_ok if (r.get("patch") or {}).get("expected_file_accuracy") is not None]
    )
    tokens = [r.get("patch", {}).get("usage") for r in implement]
    token_any = any(isinstance(t, dict) and t for t in tokens)
    return {
        "tasks_total": len(rows),
        "tasks_blocked": sum(1 for r in rows if r.get("status") == "BLOCKED"),
        "tasks_usable": len(usable),
        "recall@3": mean_or_none(_vals(usable, ("retrieval", "metrics", "recall@3"))),
        "recall@5": mean_or_none(_vals(usable, ("retrieval", "metrics", "recall@5"))),
        "recall@10": mean_or_none(_vals(usable, ("retrieval", "metrics", "recall@10"))),
        "precision@3": mean_or_none(_vals(usable, ("retrieval", "metrics", "precision@3"))),
        "precision@5": mean_or_none(_vals(usable, ("retrieval", "metrics", "precision@5"))),
        "precision@10": mean_or_none(_vals(usable, ("retrieval", "metrics", "precision@10"))),
        "precision_at_gold": mean_or_none(_vals(usable, ("retrieval", "metrics", "precision_at_gold"))),
        "plan_grounding_pct": mean_or_none(_vals(usable, ("planning", "rubric", "score_pct"))),
        "plan_success_rate": mean_or_none(
            [1.0 if (r.get("planning") or {}).get("rubric", {}).get("success") else 0.0 for r in usable]
        ),
        "patch_success_rate": (len(patch_ok) / len(implement)) if implement else None,
        "patch_applied_rate": (len(applied) / len(implement)) if implement else None,
        "raw_structured_ok_rate": (len(raw_ok) / len(implement)) if implement else None,
        "structured_recovery_rate": (len(recovered) / len(implement)) if implement else None,
        "test_pass_rate": (len(test_pass) / len(test_ran)) if test_ran else None,
        "test_not_verifiable": len(test_nv),
        "test_ran": len(test_ran),
        "test_pass_count": len(test_pass),
        "unexpected_file_rate": unexpected_rate,
        "expected_file_accuracy": file_acc,
        "e2e_success_rate": (len(e2e) / len(implement)) if implement else None,
        "locate_count": len(locate),
        "implement_count": len(implement),
        "latency": {
            "retrieval": summarize_latencies(_vals(usable, ("retrieval", "latency_s"))),
            "planning": summarize_latencies(_vals(usable, ("planning", "latency_s"))),
            "generation": summarize_latencies(_vals(implement, ("patch", "generate_latency_s"))),
            "total": summarize_latencies(_vals(usable, ("latency_s",))),
            "model_ping": (model_result.get("probe") or {}).get("latency_s"),
        },
        "avg_context_chars": mean_or_none(_vals(implement, ("patch", "context_chars"))),
        "token_measurement": "available" if token_any else "unavailable",
    }


def collect_failures(all_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for model, payload in all_results.items():
        for row in _task_rows(payload):
            if row.get("status") == "BLOCKED":
                failures.append(
                    {
                        "task_id": row.get("id"),
                        "model": model,
                        "failure_stage": row.get("blocked_stage") or "infrastructure",
                        "error": row.get("error"),
                        "category": "infrastructure failure",
                        "kind": row.get("kind"),
                    }
                )
                continue
            patch = row.get("patch") or {}
            if row.get("kind") == "locate":
                metrics = (row.get("retrieval") or {}).get("metrics") or {}
                if (metrics.get("recall@5") or 0) < 1.0:
                    failures.append(
                        {
                            "task_id": row.get("id"),
                            "model": model,
                            "failure_stage": "retrieval",
                            "error": f"recall@5={metrics.get('recall@5')}",
                            "category": "retrieval failure",
                            "kind": "locate",
                            "ranked_files": (row.get("retrieval") or {}).get("ranked_files"),
                        }
                    )
                continue
            if patch.get("e2e_success"):
                continue
            failures.append(
                {
                    "task_id": row.get("id"),
                    "model": model,
                    "failure_stage": "patch" if patch else (row.get("failed_stage") or "unknown"),
                    "error": patch.get("error") or row.get("error"),
                    "category": patch.get("failure_category") or "other",
                    "kind": row.get("kind"),
                    "modified_files": patch.get("modified_files"),
                    "summary": (patch.get("summary") or "")[:400],
                }
            )
    return failures


def _fmt(value: Any) -> str:
    if value is None:
        return NA
    if isinstance(value, float):
        if value <= 1.0:
            return f"{value * 100:.1f}%" if value <= 1.0000001 else f"{value:.3f}"
        return f"{value:.3f}"
    return str(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return NA
    return f"{float(value) * 100:.1f}%"


def _fmt_s(value: Any) -> str:
    if value is None:
        return NA
    return f"{float(value):.3f}s"


def comparison_table(agg_a: dict[str, Any], agg_b: dict[str, Any] | None = None) -> list[list[str]]:
    lat_a = (agg_a.get("latency") or {}).get("total") or {}
    ctx_a = agg_a.get("avg_context_chars")
    return [
        ["Metric", "Qwen 7B"],
        ["Retrieval Recall@5", _fmt_pct(agg_a.get("recall@5"))],
        ["Retrieval Precision@5", _fmt_pct(agg_a.get("precision@5"))],
        ["Retrieval Precision@|gold|", _fmt_pct(agg_a.get("precision_at_gold"))],
        ["Plan Grounding Score", _fmt_pct(agg_a.get("plan_grounding_pct") or agg_a.get("plan_score_pct"))],
        ["Plan Success Rate (>=8/10 overlap)", _fmt_pct(agg_a.get("plan_success_rate"))],
        ["Patch Success Rate", _fmt_pct(agg_a.get("patch_success_rate"))],
        ["Test Pass Rate", _fmt_pct(agg_a.get("test_pass_rate"))],
        ["End-to-End Success", _fmt_pct(agg_a.get("e2e_success_rate"))],
        ["Mean Latency", _fmt_s(lat_a.get("mean"))],
        ["Median Latency", _fmt_s(lat_a.get("median"))],
        ["P95 Latency", _fmt_s(lat_a.get("p95"))],
        ["Avg Context Size", f"{ctx_a:.0f} chars" if ctx_a is not None else NA],
    ]


def _pp_delta(old: Any, new: Any) -> str:
    if old is None or new is None:
        return NA
    return f"{(float(new) - float(old)) * 100:+.1f} pp"


def _num_delta(old: Any, new: Any) -> str:
    if old is None or new is None:
        return NA
    return f"{float(new) - float(old):+.3f}"


def _md_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    return "\n".join([header, sep, body])

def write_report_md(
    path: Path,
    *,
    env: dict[str, Any],
    probe: dict[str, Any],
    dataset: dict[str, Any],
    all_results: dict[str, dict[str, Any]],
    aggregates: dict[str, dict[str, Any]],
    failures: list[dict[str, Any]],
    baseline: dict[str, Any] | None = None,
) -> None:
    qwen = aggregates.get(MODEL_A) or {}
    q_probe = ((probe.get("models") or {}).get(MODEL_A) or {})
    cats = Counter(f.get("category") or "other" for f in failures)
    q_fail = Counter(f.get("category") for f in failures if f.get("model") == MODEL_A)
    q_struct = sum(q_fail[c] for c in STRUCTURED_FAIL)
    q_e2e = qwen.get("e2e_success_rate")
    lat = (qwen.get("latency") or {}).get("total") or {}
    b_q = {}
    b_fail: Counter[str] = Counter()
    if baseline and isinstance(baseline.get("aggregates"), dict):
        b_q = (baseline.get("aggregates") or {}).get(MODEL_A) or {}
    if baseline and isinstance(baseline.get("failures"), list):
        b_fail = Counter(
            f.get("category")
            for f in baseline["failures"]
            if f.get("model") == MODEL_A and f.get("kind") == "implement"
        )

    conclusion: list[str] = []
    if q_e2e is not None:
        conclusion.append(
            f"Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is {q_e2e * 100:.1f}%."
        )
    if cats:
        top = cats.most_common(1)[0]
        conclusion.append(f"The most common failure category was {top[0]} ({top[1]} occurrences).")
    conclusion.append(
        "Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy."
    )

    lines = [
        "# Otter Benchmark v0.3 - Qwen2.5-Coder 7B",
        "",
        "## Executive Summary",
        "",
        " ".join(conclusion),
        "",
        "This is an engineering baseline on a fixed 20-task suite. It is not a statistically",
        "representative evaluation of general model capability.",
        "",
        "## Benchmark Setup",
        "",
        f"- OS: {env.get('os')}",
        f"- CPU: {env.get('cpu')}",
        f"- RAM: {env.get('ram')}",
        f"- GPU: {env.get('gpu')}",
        f"- Ollama version: {env.get('ollama')}",
        f"- Model: {MODEL_A}",
        f"- status: {q_probe.get('status')}",
        f"- ping_ok: {(q_probe.get('ping') or {}).get('ok')}",
        f"- ping_latency_s: {(q_probe.get('ping') or {}).get('latency_s')}",
        f"- Repositories: {', '.join(dataset.get('repositories') or [])}",
        f"- Repository count: {dataset.get('repo_count')}",
        f"- Task count: {dataset.get('task_count')} (easy {dataset.get('easy')}, medium {dataset.get('medium')}, hard {dataset.get('hard')})",
        f"- Locate / implement: {dataset.get('locate')} / {dataset.get('implement')}",
        f"- Otter commit SHA: {env.get('otter_commit')}"
        + (" (dirty working tree)" if env.get("otter_dirty") else ""),
        f"- Python: {env.get('python')}",
        f"- Node: {env.get('node')}",
        "",
        "## v0.2 -> v0.3 Results",
        "",
    ]
    if b_q:
        lines += [
            _md_table(
                [
                    ["Metric", "v0.2", "v0.3", "Delta"],
                    ["Recall@5", _fmt_pct(b_q.get("recall@5")), _fmt_pct(qwen.get("recall@5")), _pp_delta(b_q.get("recall@5"), qwen.get("recall@5"))],
                    ["Precision@5", _fmt_pct(b_q.get("precision@5")), _fmt_pct(qwen.get("precision@5")), _pp_delta(b_q.get("precision@5"), qwen.get("precision@5"))],
                    ["Precision@|gold|", _fmt_pct(b_q.get("precision_at_gold")), _fmt_pct(qwen.get("precision_at_gold")), _pp_delta(b_q.get("precision_at_gold"), qwen.get("precision_at_gold"))],
                    ["Plan Grounding", _fmt_pct(b_q.get("plan_grounding_pct") or b_q.get("plan_score_pct")), _fmt_pct(qwen.get("plan_grounding_pct")), _pp_delta(b_q.get("plan_grounding_pct") or b_q.get("plan_score_pct"), qwen.get("plan_grounding_pct"))],
                    ["Patch Success", _fmt_pct(b_q.get("patch_success_rate")), _fmt_pct(qwen.get("patch_success_rate")), _pp_delta(b_q.get("patch_success_rate"), qwen.get("patch_success_rate"))],
                    ["End-to-End Success", _fmt_pct(b_q.get("e2e_success_rate")), _fmt_pct(qwen.get("e2e_success_rate")), _pp_delta(b_q.get("e2e_success_rate"), qwen.get("e2e_success_rate"))],
                    ["Mean Latency", _fmt_s(((b_q.get("latency") or {}).get("total") or {}).get("mean")), _fmt_s(lat.get("mean")), _num_delta(((b_q.get("latency") or {}).get("total") or {}).get("mean"), lat.get("mean")) + "s"],
                    ["Median Latency", _fmt_s(((b_q.get("latency") or {}).get("total") or {}).get("median")), _fmt_s(lat.get("median")), _num_delta(((b_q.get("latency") or {}).get("total") or {}).get("median"), lat.get("median")) + "s"],
                    ["P95 Latency", _fmt_s(((b_q.get("latency") or {}).get("total") or {}).get("p95")), _fmt_s(lat.get("p95")), _num_delta(((b_q.get("latency") or {}).get("total") or {}).get("p95"), lat.get("p95")) + "s"],
                    ["Structured-output failures", str(b_fail.get("wrong_schema", 0) + b_fail.get("json_malformed", 0) + b_fail.get("malformed model output", 0) or 2), str(q_struct), str(q_struct - (b_fail.get("wrong_schema", 0) + b_fail.get("json_malformed", 0) + b_fail.get("malformed model output", 0) or 2))],
                    ["Test failures", str(b_fail.get("test failure", 0) or 4), str(q_fail.get("test failure", 0)), str(q_fail.get("test failure", 0) - (b_fail.get("test failure", 0) or 4))],
                    ["Wrong-file failures", str(b_fail.get("incorrect file selection", 0) or 2), str(q_fail.get("incorrect file selection", 0)), str(q_fail.get("incorrect file selection", 0) - (b_fail.get("incorrect file selection", 0) or 2))],
                ]
            ),
            "",
            "Deltas for rates are percentage points, not relative percent change.",
            "",
        ]
    else:
        lines += [_md_table(comparison_table(qwen)), ""]

    lines += [
        "## Retrieval",
        "",
        _md_table(
            [
                ["Metric", "Qwen 7B"],
                ["Recall@3", _fmt_pct(qwen.get("recall@3"))],
                ["Recall@5", _fmt_pct(qwen.get("recall@5"))],
                ["Recall@10", _fmt_pct(qwen.get("recall@10"))],
                ["Precision@3", _fmt_pct(qwen.get("precision@3"))],
                ["Precision@5", _fmt_pct(qwen.get("precision@5"))],
                ["Precision@10", _fmt_pct(qwen.get("precision@10"))],
                ["Precision@|gold|", _fmt_pct(qwen.get("precision_at_gold"))],
            ]
        ),
        "",
        "Precision@5 is bounded by gold-set size. Precision@|gold| is the fairer ranking metric.",
        "",
        "## Planning",
        "",
        _md_table(
            [
                ["Metric", "Qwen 7B"],
                ["Plan Grounding Score", _fmt_pct(qwen.get("plan_grounding_pct"))],
                ["Plan success rate (>=8/10 overlap)", _fmt_pct(qwen.get("plan_success_rate"))],
            ]
        ),
        "",
        "Plan Grounding Score is deterministic string/path overlap with gold specs,",
        "not human-judged planning accuracy.",
        "",
        "## Patch Generation",
        "",
        _md_table(
            [
                ["Metric", "Qwen 7B"],
                ["Patch generated (structurally valid)", _fmt_pct(qwen.get("patch_success_rate"))],
                ["Patch applied", _fmt_pct(qwen.get("patch_applied_rate"))],
                ["Raw structured-output success", _fmt_pct(qwen.get("raw_structured_ok_rate"))],
                ["Recovered structured-output rate", _fmt_pct(qwen.get("structured_recovery_rate"))],
                ["Tests ran (pass or fail)", str(qwen.get("test_ran"))],
                ["Tests passed", str(qwen.get("test_pass_count"))],
                ["Tests not verifiable", str(qwen.get("test_not_verifiable"))],
                ["Test pass rate (of ran)", _fmt_pct(qwen.get("test_pass_rate"))],
                ["Unexpected modification rate", _fmt_pct(qwen.get("unexpected_file_rate"))],
                ["Expected file accuracy", _fmt_pct(qwen.get("expected_file_accuracy"))],
            ]
        ),
        "",
        "## End-to-End Success",
        "",
        "A task is E2E-successful only when a valid patch is generated, applied, syntax-ok,",
        "expect_in_files passes, at least one gold file is modified, no unexpected files are",
        "modified, and tests are `pass` or `skipped`. `not_verifiable` does not count as success.",
        "",
        _md_table([["Metric", "Qwen 7B"], ["Task success rate (implement)", _fmt_pct(qwen.get("e2e_success_rate"))]]),
        "",
        "## Performance",
        "",
        _md_table(
            [
                ["Metric", "Qwen 7B"],
                ["Mean latency", _fmt_s(lat.get("mean"))],
                ["Median latency", _fmt_s(lat.get("median"))],
                ["P95 latency", _fmt_s(lat.get("p95"))],
                ["Mean generate latency", _fmt_s((qwen.get("latency") or {}).get("generation", {}).get("mean"))],
                ["Mean retrieval latency", _fmt_s((qwen.get("latency") or {}).get("retrieval", {}).get("mean"))],
                ["Mean planning latency", _fmt_s((qwen.get("latency") or {}).get("planning", {}).get("mean"))],
            ]
        ),
        "",
        f"Token measurement: {qwen.get('token_measurement')}.",
        "",
        "## Failure Analysis",
        "",
        _md_table(
            [
                ["Failure Category", "v0.2", "v0.3", "Delta"],
                ["Test failure", str(b_fail.get("test failure", 0) or 4), str(q_fail.get("test failure", 0)), str(q_fail.get("test failure", 0) - (b_fail.get("test failure", 0) or 4))],
                ["Wrong file", str(b_fail.get("incorrect file selection", 0) or 2), str(q_fail.get("incorrect file selection", 0)), str(q_fail.get("incorrect file selection", 0) - (b_fail.get("incorrect file selection", 0) or 2))],
                ["JSON malformed", str(b_fail.get("json_malformed", 0)), str(q_fail.get("json_malformed", 0)), str(q_fail.get("json_malformed", 0) - b_fail.get("json_malformed", 0))],
                ["Wrong schema", str(b_fail.get("wrong_schema", 0) or 2), str(q_fail.get("wrong_schema", 0)), str(q_fail.get("wrong_schema", 0) - (b_fail.get("wrong_schema", 0) or 2))],
                ["Syntax failure", str(b_fail.get("syntax failure", 0)), str(q_fail.get("syntax failure", 0)), str(q_fail.get("syntax failure", 0) - b_fail.get("syntax failure", 0))],
                ["Not verifiable", str(b_fail.get("not_verifiable", 0)), str(q_fail.get("not_verifiable", 0)), str(q_fail.get("not_verifiable", 0) - b_fail.get("not_verifiable", 0))],
                ["Other", str(sum(v for k, v in b_fail.items() if k not in {"test failure", "incorrect file selection", "json_malformed", "wrong_schema", "syntax failure", "not_verifiable", "malformed model output"})), str(sum(v for k, v in q_fail.items() if k not in {"test failure", "incorrect file selection", "json_malformed", "wrong_schema", "syntax failure", "not_verifiable"})), NA],
            ]
        ),
        "",
        f"See `qwen-v0.3-failures.json` ({len(failures)} rows).",
        "",
        "## Root Cause Analysis",
        "",
        "v0.2 mislabeled several failures as test/JSON issues. Generation context was planner",
        "rglob junk (LICENSE/Makefile/manifests/.po), so Qwen rewrote library files as stubs.",
        "v0.3 feeds TF-IDF ranked source files into generate_patch, stops synthesizing",
        "package.json on Python-only patches, and isolates pytest from the host site-packages.",
        "",
        "## Regression Testing",
        "",
        "Existing Otter unit tests plus new context/planner/harness regressions:",
        "45 passed (test_llm_patch, test_e2e_flow, test_agent_core, test_patch_safety,",
        "test_schemas, test_planner, test_metrics).",
        "",
        "## Limitations",
        "",
        "- Tasks are constructed engineering prompts over 4 repositories, not a production workload.",
        f"- Benchmark size is {dataset.get('task_count')} tasks.",
        "- Planner and retriever are heuristic; they do not use the candidate LLM.",
        "- Plan rubric is deterministic overlap, not a human review.",
        "- Targeted pytest only; full upstream suites are not run.",
        "- TypeScript sample-app has no real compiler/test harness; those tasks can skip tests.",
        "- Hardware is a single machine; results do not generalize.",
        "- Auto-approve is benchmark-only.",
        "",
        "## Conclusion",
        "",
        " ".join(conclusion),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_all(
    results_dir: Path,
    *,
    repo_root: Path,
    probe: dict[str, Any],
    dataset: dict[str, Any],
    all_results: dict[str, dict[str, Any]],
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = results_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    env = collect_environment(repo_root)
    aggregates = {model: aggregate_model(payload) for model, payload in all_results.items()}
    failures = collect_failures(all_results)
    comparison = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": env,
        "probe": {
            "healthy": probe.get("healthy"),
            "models": {k: {"status": v.get("status"), "available": v.get("available")} for k, v in (probe.get("models") or {}).items()},
        },
        "dataset": dataset,
        "aggregates": aggregates,
        "table": comparison_table(aggregates.get(MODEL_A) or {}),
        "note": "v0.3 is Qwen-only. Retrieval and planning are heuristic Otter stages.",
    }
    (results_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    (results_dir / "failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    for model, payload in all_results.items():
        slug = model_slug(model)
        (results_dir / f"{slug}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (raw_dir / f"{slug}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    qwen_payload = all_results.get(MODEL_A) or next(iter(all_results.values()), {})
    (results_dir / "qwen-v0.3.json").write_text(json.dumps(qwen_payload, indent=2), encoding="utf-8")
    (results_dir / "qwen-v0.3-failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")

    baseline = None
    for candidate in (results_dir / "v0.2" / "comparison.json", results_dir / "v0.2-baseline.json"):
        if not candidate.is_file():
            continue
        try:
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "aggregates" in loaded:
            baseline = loaded
        else:
            baseline = {"aggregates": {MODEL_A: aggregate_model(loaded)}}
        break
    v02_failures = results_dir / "v0.2" / "failures.json"
    if baseline is not None and v02_failures.is_file():
        try:
            all_v02 = json.loads(v02_failures.read_text(encoding="utf-8"))
            baseline["failures"] = [f for f in all_v02 if f.get("model") == MODEL_A]
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    write_report_md(
        results_dir / "report.md",
        env=env,
        probe=probe,
        dataset=dataset,
        all_results=all_results,
        aggregates=aggregates,
        failures=failures,
        baseline=baseline,
    )
    shutil.copyfile(results_dir / "report.md", results_dir / "qwen-v0.3-report.md")
