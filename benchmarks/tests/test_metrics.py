"""Unit tests for benchmark metrics and plan rubric. No LLM."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.runners.metrics import (
    precision_at_k,
    recall_at_k,
    retrieval_metrics,
    score_plan,
    unique_ranked_files,
)


def test_pytest_collection_import_is_not_verifiable():
    from benchmarks.runners.patch import _classify_pytest_result

    output = "ImportError while loading conftest\nNo module named 'httpx'\n"
    classified = _classify_pytest_result(1, output)
    assert classified["status"] == "not_verifiable"
    assert classified["passed"] is None
    failed = _classify_pytest_result(1, "E   assert 1 == 2\n")
    assert failed["status"] == "fail"
    assert failed["passed"] is False
    passed = _classify_pytest_result(0, "2 passed\n")
    assert passed["status"] == "pass"


def test_python_multipart_warning_plus_missing_local_module_is_fail():
    from benchmarks.runners.patch import _classify_pytest_result

    output = (
        "Please use `import python_multipart` instead.\n"
        "E   ModuleNotFoundError: No module named 'starlette.middleware.request_id'\n"
    )
    classified = _classify_pytest_result(1, output)
    assert classified["status"] == "fail"
    assert classified["passed"] is False
    infra = _classify_pytest_result(1, "ModuleNotFoundError: No module named 'httpx'\n")
    assert infra["status"] == "not_verifiable"


def test_edit_target_errors_are_quality_gate():
    from benchmarks.runners.patch import classify_failure

    category = classify_failure(
        generation_ok=False,
        todo_only=False,
        quality_error=None,
        apply_error=None,
        syntax={"ok": False},
        tests={"status": "skipped"},
        expected_hit=False,
        unexpected=[],
        generate_error="qwen2.5-coder:7b: Edit target not unique in src/click/types.py",
    )
    assert category == "quality_gate"
    structured = classify_failure(
        generation_ok=False,
        todo_only=False,
        quality_error=None,
        apply_error=None,
        syntax={"ok": False},
        tests={"status": "skipped"},
        expected_hit=False,
        unexpected=[],
        generate_error="QUALITY_GATE:\n    category: destructive_rewrite\n    file: bottle.py\n    reason: stub",
    )
    assert structured == "quality_gate"


def test_recall_and_precision_at_k():
    retrieved = ["a.py", "b.py", "c.py", "d.py"]
    gold = ["a.py", "z.py"]
    assert recall_at_k(retrieved, gold, 1) == 0.5
    assert recall_at_k(retrieved, gold, 3) == 0.5
    assert precision_at_k(retrieved, gold, 3) == 1 / 3
    assert precision_at_k([], gold, 3) == 0.0
    assert recall_at_k(retrieved, [], 3) == 0.0


def test_unique_ranked_files_dedupes_chunks():
    hits = [
        {"rel_path": "src/auth.ts"},
        {"path": "src/auth.ts"},
        {"rel_path": "src/routes.ts"},
    ]
    assert unique_ranked_files(hits) == ["src/auth.ts", "src/routes.ts"]


def test_retrieval_metrics_keys():
    metrics = retrieval_metrics(["src/a.py"], ["src/a.py", "src/b.py"])
    assert set(metrics) == {
        "recall@3",
        "recall@5",
        "recall@10",
        "precision@3",
        "precision@5",
        "precision@10",
        "precision_at_gold",
    }
    assert metrics["recall@3"] == 0.5
    assert metrics["precision@3"] == 1 / 3
    assert metrics["precision_at_gold"] == 0.5


def test_plan_rubric_all_correct():
    plan = {
        "title": "Plan: Add email validation",
        "summary": "Add email validation. Return a client error for invalid email. Add regression coverage.",
        "steps": ["Inspect src/routes.py", "Add tests/test_auth.py"],
        "affected_files": ["src/routes.py", "tests/test_auth.py"],
        "dependencies": ["Request and response contract", "API integration tests"],
        "risks": [],
    }
    gold = {
        "relevant_files": ["src/routes.py", "tests/test_auth.py"],
        "expected_changes": [
            "Add email validation",
            "Return a client error for invalid email",
            "Add regression coverage",
        ],
        "dependencies": ["Request and response contract", "API integration tests"],
        "verification": {"tests": ["tests/test_auth.py"]},
    }
    scored = score_plan(plan, gold, ["src/routes.py", "tests/test_auth.py", "README.md"])
    assert scored["A_files"] == 2
    assert scored["B_approach"] == 2
    assert scored["C_dependencies"] == 2
    assert scored["D_verification"] == 2
    assert scored["E_no_invented"] == 2
    assert scored["total"] == 10
    assert scored["success"] is True


def test_plan_rubric_invented_files_and_misses():
    plan = {
        "title": "Plan",
        "summary": "unrelated",
        "steps": ["do stuff"],
        "affected_files": ["does/not/exist.py", "also/missing.py"],
        "dependencies": [],
        "risks": [],
    }
    gold = {
        "relevant_files": ["src/real.py"],
        "expected_changes": ["Add email validation"],
        "dependencies": ["Database migration"],
        "verification": {"tests": ["tests/test_real.py"]},
    }
    scored = score_plan(plan, gold, ["src/real.py"])
    assert scored["A_files"] == 0
    assert scored["B_approach"] == 0
    assert scored["C_dependencies"] == 0
    assert scored["D_verification"] == 0
    assert scored["E_no_invented"] == 0
    assert scored["success"] is False
