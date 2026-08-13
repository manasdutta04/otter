"""Generate / approve / apply using Otter's real coding path in an isolated copy."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from packages.agent.context import build_context
from packages.agent.model_adapt import budget_for_model
from packages.agent.orchestrate import begin_implement, prepare_engineering_run
from packages.agent.state_machine import IllegalTransition, assert_can_apply, assert_can_generate

from benchmarks.runners.metrics import _norm_path
from benchmarks.runners.model_runner import pin_model

SKIP_COPY = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", "dist", "build", ".mypy_cache"}


def copy_workspace(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in SKIP_COPY}

    shutil.copytree(src, dest, ignore=ignore)


def _safe_target(root: Path, rel: str) -> Path | None:
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts or candidate.name in {"", ".", ".."}:
        return None
    target = (root / candidate).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return target


def apply_files(root: Path, files: list[dict[str, str]]) -> list[str]:
    written: list[str] = []
    for item in files:
        rel = _norm_path(str(item.get("path") or ""))
        target = _safe_target(root, rel)
        if target is None:
            raise ValueError(f"unsafe patch path: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(item.get("content") or ""), encoding="utf-8")
        written.append(rel)
    return written


def syntax_check(root: Path, files: list[str], lang: str | None) -> dict[str, Any]:
    py_files = [f for f in files if f.endswith(".py")]
    if lang == "py" or py_files:
        errors: list[str] = []
        for rel in py_files:
            path = root / rel
            if not path.is_file():
                errors.append(f"missing {rel}")
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=rel)
            except SyntaxError as error:
                errors.append(f"{rel}: {error}")
        return {"ok": not errors, "checked": py_files, "errors": errors}
    if lang == "ts":
        return {"ok": True, "checked": files, "errors": [], "note": "no TypeScript compiler in suite; syntax skipped"}
    return {"ok": True, "checked": [], "errors": [], "note": "no syntax language"}


def expect_in_files(root: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
    if not specs:
        return {"ok": True, "missing": []}
    missing: list[str] = []
    for spec in specs:
        rel = _norm_path(str(spec.get("path") or ""))
        path = root / rel
        if not path.is_file():
            missing.append(f"{rel} (file missing)")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in spec.get("contains") or []:
            if str(needle) not in text:
                missing.append(f"{rel} missing {needle!r}")
    return {"ok": not missing, "missing": missing}


_THIRD_PARTY_ROOTS = frozenset(
    {"httpx", "python_multipart", "multipart", "anyio", "sniffio", "itsdangerous"}
)
_MODULE_NOT_FOUND_RE = re.compile(r"No module named ['\"]([^'\"]+)['\"]")


def _classify_pytest_result(returncode: int, output: str) -> dict[str, Any]:
    if returncode == 0:
        return {"status": "pass", "passed": True}
    missing = _MODULE_NOT_FOUND_RE.findall(output or "")
    if missing:
        local = [name for name in missing if name.split(".")[0] not in _THIRD_PARTY_ROOTS]
        if local:
            return {"status": "fail", "passed": False}
        return {"status": "not_verifiable", "passed": None}
    return {"status": "fail", "passed": False}


def run_gold_tests(root: Path, test_paths: list[str], timeout_s: int = 180) -> dict[str, Any]:
    if not test_paths:
        return {"status": "skipped", "passed": None, "output": "no gold tests", "command": None}
    python = sys.executable
    if not python:
        return {"status": "BLOCKED", "passed": None, "output": "python not on PATH", "command": None}
    cmd = [
        python,
        "-m",
        "pytest",
        "-q",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",
        "-o",
        "filterwarnings=",
        *test_paths,
    ]
    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    extra = [str(root), str(root / "src")]
    env["PYTHONPATH"] = os.pathsep.join(extra + [env.get("PYTHONPATH") or ""])
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-4000:]
        classified = _classify_pytest_result(result.returncode, output)
        return {
            "status": classified["status"],
            "passed": classified["passed"],
            "output": output,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"status": "fail", "passed": False, "output": "pytest timed out", "command": " ".join(cmd)}
    except OSError as error:
        return {"status": "infrastructure_error", "passed": None, "output": str(error), "command": " ".join(cmd)}


def classify_failure(
    *,
    generation_ok: bool,
    todo_only: bool,
    quality_error: str | None,
    apply_error: str | None,
    syntax: dict[str, Any],
    tests: dict[str, Any],
    expected_hit: bool,
    unexpected: list[str],
    generate_error: str | None,
) -> str | None:
    err = (generate_error or quality_error or apply_error or "")
    low = err.lower()
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if not generation_ok:
        if "no json object" in low:
            return "json_malformed"
        if "invalid patch shape" in low or "no usable files" in low:
            return "wrong_schema"
        if "truncated" in low:
            return "json_truncated"
        if (
            "rejected low-quality" in low
            or "quality_gate" in low
            or "auth change" in low
            or "imports `" in low
            or "edit target" in low
            or "edit_target" in low
            or "destructive rewrite" in low
            or "destructive_rewrite" in low
            or "truncated patch" in low
        ):
            return "quality_gate"
        if "connect" in low or "10061" in low or "ollama" in low:
            return "infrastructure failure"
        if "json" in low or "malformed" in low:
            return "json_malformed"
        return "malformed model output"
    if todo_only:
        return "malformed model output"
    if quality_error:
        if "invent" in low or "orm" in low:
            return "hallucinated API"
        return "quality_gate"
    if apply_error:
        return "syntax failure" if "unsafe" not in low else "incorrect file selection"
    if not expected_hit:
        return "incorrect file selection"
    if unexpected:
        return "incorrect file selection"
    if not syntax.get("ok"):
        return "syntax failure"
    if tests.get("status") == "fail":
        return "test failure"
    if tests.get("status") in {"BLOCKED", "not_verifiable", "infrastructure_error"}:
        return "not_verifiable" if tests.get("status") == "not_verifiable" else "infrastructure failure"
    return None


async def run_patch(
    *,
    repo_root: Path,
    work_root: Path,
    task_id: str,
    prompt: str,
    gold: dict[str, Any],
    model: str,
    intelligence: dict[str, Any] | None,
    plan: dict[str, Any] | None,
    extra_paths: list[str] | None = None,
) -> dict[str, Any]:
    from app.llm import (
        CONTEXT_CHARS_PER_FILE,
        CONTEXT_FILE_LIMIT,
        PatchGenerationError,
        generate_patch,
        is_todo_only_patch,
    )

    gold_files = [_norm_path(p) for p in (gold.get("relevant_files") or [])]
    allowed_extra = {_norm_path(p) for p in (gold.get("allowed_extra_files") or [])}
    verification = gold.get("verification") or {}
    copy_started = time.perf_counter()
    copy_workspace(repo_root, work_root)
    copy_s = time.perf_counter() - copy_started

    status = "ready_for_approval"
    try:
        assert_can_generate(status)
    except IllegalTransition as error:
        return {"ok": False, "error": str(error), "failure_category": "other"}

    budget = budget_for_model(model)
    ctx_started = time.perf_counter()
    eng = prepare_engineering_run(
        repository_id=task_id,
        request=prompt,
        repo_root=work_root,
        model=model,
        intelligence=intelligence,
        plan=plan,
        extra_paths=extra_paths,
    )
    begin_implement(eng)
    bundle = eng.context or build_context(
        work_root,
        prompt,
        intelligence=intelligence,
        plan=plan,
        model=model,
        budget=budget,
        extra_paths=extra_paths,
    )
    bounded = bundle.bounded_files(budget.max_context_files, budget.max_chars_per_file)
    files = [{"path": f.path, "content": f.content} for f in bounded]
    files = files[:CONTEXT_FILE_LIMIT]
    for item in files:
        item["content"] = item["content"][:CONTEXT_CHARS_PER_FILE]
    apply_originals: dict[str, str] = {}
    for item in files:
        disk = work_root / item["path"]
        if disk.is_file():
            try:
                apply_originals[item["path"]] = disk.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                apply_originals[item["path"]] = item["content"]
    context_chars = sum(len(item["content"]) for item in files)
    context_s = time.perf_counter() - ctx_started

    gen_started = time.perf_counter()
    generate_error = None
    raw_completion = None
    quality_gate = None
    proposal: dict[str, Any] | None = None
    try:
        with pin_model(model):
            proposal = await generate_patch(
                prompt,
                files,
                plan_context=plan,
                apply_originals=apply_originals,
            )
    except PatchGenerationError as error:
        generate_error = str(error)
        raw_completion = getattr(error, "raw_completion", None)
        quality_gate = getattr(error, "quality_gate", None)
    except Exception as error:  # noqa: BLE001
        generate_error = str(error)
    generate_s = time.perf_counter() - gen_started

    patch_files: list[dict[str, str]] = []
    if proposal:
        for item in proposal.get("files") or []:
            if isinstance(item, dict) and item.get("path") is not None:
                patch_files.append({"path": _norm_path(str(item["path"])), "content": str(item.get("content") or "")})

    originals = {item["path"]: item["content"] for item in files}
    # generate_patch already ran validate_patch_quality; do not re-run it with
    # incomplete context originals (that double-count quality-gate failures).
    todo_only = bool(patch_files) and is_todo_only_patch(patch_files, originals)
    quality_error = None

    generation_ok = bool(proposal) and bool(patch_files) and not todo_only and not generate_error
    modified = [_norm_path(item["path"]) for item in patch_files]
    expected_hit = any(p in gold_files for p in modified)
    unexpected = [p for p in modified if p not in gold_files and p not in allowed_extra]

    apply_error = None
    applied = False
    apply_s = 0.0
    if generation_ok:
        status = "patch_ready"
        status = "approved"
        try:
            assert_can_apply(status)
            apply_started = time.perf_counter()
            apply_files(work_root, patch_files)
            apply_s = time.perf_counter() - apply_started
            applied = True
        except (IllegalTransition, ValueError, OSError) as error:
            apply_error = str(error)

    syntax = {"ok": False, "checked": [], "errors": ["not applied"]}
    expects = {"ok": False, "missing": ["not applied"]}
    tests = {"status": "skipped", "passed": None, "output": "not applied", "command": None}
    test_s = 0.0
    if applied:
        syntax = syntax_check(work_root, modified, verification.get("syntax"))
        expects = expect_in_files(work_root, list(verification.get("expect_in_files") or []))
        test_started = time.perf_counter()
        tests = run_gold_tests(work_root, list(verification.get("tests") or []))
        test_s = time.perf_counter() - test_started

    e2e = bool(
        generation_ok
        and applied
        and syntax.get("ok")
        and expects.get("ok")
        and expected_hit
        and not unexpected
        and tests.get("status") in {"pass", "skipped"}
    )
    category = None if e2e else classify_failure(
        generation_ok=generation_ok,
        todo_only=todo_only,
        quality_error=quality_error,
        apply_error=apply_error,
        syntax=syntax,
        tests=tests,
        expected_hit=expected_hit,
        unexpected=unexpected,
        generate_error=generate_error,
    )
    if applied and not expects.get("ok") and category is None:
        category = "test failure"

    tokens_available = False
    return {
        "ok": generation_ok,
        "generation_succeeded": generation_ok,
        "applied": applied,
        "e2e_success": e2e,
        "todo_only": todo_only,
        "summary": str((proposal or {}).get("summary") or ""),
        "model_reported": (proposal or {}).get("model"),
        "modified_files": modified,
        "expected_files_hit": expected_hit,
        "expected_file_accuracy": (len(set(modified) & set(gold_files)) / len(gold_files)) if gold_files else 0.0,
        "unexpected_files": unexpected,
        "context_files": [item["path"] for item in files],
        "context_file_count": len(files),
        "context_chars": context_chars,
        "token_measurement": "unavailable" if not tokens_available else "available",
        "usage": None,
        "syntax": syntax,
        "expect_in_files": expects,
        "tests": tests,
        "copy_latency_s": copy_s,
        "context_latency_s": context_s,
        "generate_latency_s": generate_s,
        "apply_latency_s": apply_s,
        "test_latency_s": test_s,
        "error": generate_error or quality_error or apply_error,
        "failure_category": category,
        "status_machine": status,
        "structured_recovery": bool((proposal or {}).get("structured_recovery")),
        "raw_structured_ok": (proposal or {}).get("raw_structured_ok"),
        "raw_completion_preview": raw_completion,
        "first_attempt_latency_s": (proposal or {}).get("first_attempt_latency"),
        "retry_latency_s": (proposal or {}).get("retry_latency"),
        "quality_gate": quality_gate,
    }
