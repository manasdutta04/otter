"""Deterministic retrieval / plan / latency metrics. No LLM judging."""

from __future__ import annotations

from statistics import mean, median
from typing import Any, Iterable, Sequence


def _norm_path(path: str) -> str:
    return str(path or "").replace("\\", "/").lstrip("./")


def unique_ranked_files(hits: Sequence[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for hit in hits:
        path = _norm_path(str(hit.get("rel_path") or hit.get("path") or ""))
        if not path or path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def recall_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    gold_set = {_norm_path(p) for p in gold if p}
    if not gold_set:
        return 0.0
    top = {_norm_path(p) for p in list(retrieved)[:k]}
    return len(gold_set & top) / len(gold_set)


def precision_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    if k <= 0:
        return 0.0
    gold_set = {_norm_path(p) for p in gold if p}
    top = [_norm_path(p) for p in list(retrieved)[:k]]
    if not top:
        return 0.0
    hits = sum(1 for p in top if p in gold_set)
    return hits / k


def retrieval_metrics(retrieved: Sequence[str], gold: Sequence[str]) -> dict[str, float]:
    gold_n = len([p for p in gold if p])
    return {
        "recall@3": recall_at_k(retrieved, gold, 3),
        "recall@5": recall_at_k(retrieved, gold, 5),
        "recall@10": recall_at_k(retrieved, gold, 10),
        "precision@3": precision_at_k(retrieved, gold, 3),
        "precision@5": precision_at_k(retrieved, gold, 5),
        "precision@10": precision_at_k(retrieved, gold, 10),
        "precision_at_gold": precision_at_k(retrieved, gold, max(gold_n, 1)) if gold_n else 0.0,
    }


def _plan_text(plan: dict[str, Any]) -> str:
    parts = [
        str(plan.get("title") or ""),
        str(plan.get("summary") or ""),
        " ".join(str(s) for s in (plan.get("steps") or [])),
        " ".join(str(s) for s in (plan.get("affected_files") or [])),
        " ".join(str(s) for s in (plan.get("dependencies") or [])),
        " ".join(str(s) for s in (plan.get("risks") or [])),
    ]
    return " ".join(parts).lower()


def score_files(affected: Sequence[str], gold_files: Sequence[str]) -> int:
    gold_set = {_norm_path(p) for p in gold_files if p}
    if not gold_set:
        return 2
    got = {_norm_path(p) for p in affected}
    overlap = gold_set & got
    if overlap == gold_set:
        return 2
    if overlap:
        return 1
    return 0


def score_approach(plan: dict[str, Any], expected_changes: Sequence[str]) -> int:
    if not expected_changes:
        return 2
    text = _plan_text(plan)
    hits = sum(1 for phrase in expected_changes if phrase.lower() in text)
    if hits == len(expected_changes):
        return 2
    if hits:
        return 1
    return 0


def score_dependencies(plan: dict[str, Any], gold_deps: Sequence[str], root_exists: bool) -> int:
    deps = [str(d) for d in (plan.get("dependencies") or [])]
    if not gold_deps:
        if deps and root_exists:
            return 2
        return 1 if deps else 0
    text = " ".join(deps).lower()
    hits = sum(1 for d in gold_deps if d.lower() in text)
    if hits == len(gold_deps):
        return 2
    if hits:
        return 1
    return 0


def score_verification(plan: dict[str, Any], test_paths: Sequence[str]) -> int:
    if not test_paths:
        text = _plan_text(plan)
        return 2 if "test" in text else 1
    text = _plan_text(plan)
    hits = sum(1 for p in test_paths if _norm_path(p).lower() in text)
    if hits == len(test_paths):
        return 2
    if hits:
        return 1
    return 0


def score_no_invented(affected: Sequence[str], existing_files: Sequence[str]) -> int:
    if not affected:
        return 1
    existing = {_norm_path(p) for p in existing_files}
    missing = [_norm_path(p) for p in affected if _norm_path(p) not in existing]
    if not missing:
        return 2
    if len(missing) * 2 <= len(affected):
        return 1
    return 0


def score_plan(
    plan: dict[str, Any],
    gold: dict[str, Any],
    existing_files: Sequence[str],
) -> dict[str, Any]:
    affected = [str(p) for p in (plan.get("affected_files") or [])]
    gold_files = [str(p) for p in (gold.get("relevant_files") or [])]
    expected = [str(p) for p in (gold.get("expected_changes") or [])]
    gold_deps = [str(p) for p in (gold.get("dependencies") or [])]
    tests = [str(p) for p in ((gold.get("verification") or {}).get("tests") or [])]
    all_exist = bool(affected) and all(_norm_path(p) in {_norm_path(x) for x in existing_files} for p in affected)
    a = score_files(affected, gold_files)
    b = score_approach(plan, expected)
    c = score_dependencies(plan, gold_deps, all_exist or not affected)
    d = score_verification(plan, tests)
    e = score_no_invented(affected, existing_files)
    total = a + b + c + d + e
    return {
        "A_files": a,
        "B_approach": b,
        "C_dependencies": c,
        "D_verification": d,
        "E_no_invented": e,
        "total": total,
        "max": 10,
        "score_pct": total / 10.0,
        "success": total >= 8,
    }


def percentile(values: Sequence[float], p: float) -> float | None:
    nums = sorted(float(v) for v in values if v is not None)
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    idx = min(len(nums) - 1, max(0, round((p / 100.0) * (len(nums) - 1))))
    return nums[idx]


def summarize_latencies(values: Iterable[float]) -> dict[str, float | None]:
    nums = [float(v) for v in values]
    if not nums:
        return {"mean": None, "median": None, "p95": None, "n": 0}
    return {
        "mean": mean(nums),
        "median": median(nums),
        "p95": percentile(nums, 95),
        "n": len(nums),
    }


def mean_or_none(values: Sequence[float]) -> float | None:
    nums = [float(v) for v in values]
    if not nums:
        return None
    return mean(nums)
