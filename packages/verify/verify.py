"""Independent verification of a repository working tree / proposed change."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from packages.architecture import guard_proposal
from packages.impact import impact_from_focus

from .runners import run_allowlisted_checks


def _git_diff_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=20,
            )
            files = []
            for line in result.stdout.splitlines():
                path = line[3:].strip() if len(line) > 3 else ""
                if path:
                    files.append(path.replace("\\", "/"))
            return files[:40]
        return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()][:40]
    except (OSError, subprocess.TimeoutExpired):
        return []


def verify_repository(
    root: Path,
    *,
    proposal: str | None = None,
    focus_paths: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(root)
    changed = focus_paths or _git_diff_files(root)
    checks = run_allowlisted_checks(root)
    impact = impact_from_focus(root, focus_paths=changed[:12], depth=2) if changed else {
        "risk": "low",
        "affected_tests": [],
        "risks": [],
    }
    architecture = guard_proposal(
        root,
        proposal=proposal or f"Verify changes to: {', '.join(changed[:8]) or 'working tree'}",
        target_paths=changed,
    )

    security_risks: list[str] = []
    for path in changed[:20]:
        low = path.lower()
        if any(tok in low for tok in (".env", "secret", "credential", "id_rsa")):
            security_risks.append(f"Sensitive path touched: {path}")

    missing_tests: list[str] = []
    if changed and not any("test" in p.lower() or p.endswith(".spec.ts") for p in changed):
        if impact.get("affected_tests"):
            missing_tests.append("Changed production files without updating related tests in the diff.")
        else:
            missing_tests.append("No test files in the change set.")

    regressions = list(impact.get("risks") or [])[:8]

    def _bucket(name: str) -> dict[str, Any]:
        return checks.get(name) or {"status": "skipped", "passed": None, "output": "not run"}

    hard_fail = any(v.get("passed") is False for k, v in checks.items() if k in ("test", "typecheck", "build"))
    arch_fail = architecture.get("status") == "fail"
    if hard_fail or security_risks:
        verdict = "blocked"
    elif arch_fail or missing_tests or any(v.get("passed") is False for v in checks.values()):
        verdict = "review"
    else:
        verdict = "pass"

    recommendations: list[str] = []
    if hard_fail:
        recommendations.append("Fix failing tests/typecheck/build before merge.")
    if arch_fail:
        recommendations.append("Resolve architecture violations reported by otter_guard.")
    if missing_tests:
        recommendations.append("Add or update tests for the changed behavior.")
    if security_risks:
        recommendations.append("Review secret/credential path changes carefully.")

    return {
        "verdict": verdict,
        "changed_files": changed,
        "tests": _bucket("test"),
        "typecheck": _bucket("typecheck"),
        "lint": _bucket("lint"),
        "build": _bucket("build"),
        "architecture": architecture,
        "security": {"risks": security_risks, "status": "blocked" if security_risks else "pass"},
        "dependencies": {
            "status": "review" if any(p.endswith("package.json") or p.endswith("requirements.txt") for p in changed) else "pass",
            "notes": [p for p in changed if p.endswith(("package.json", "package-lock.json", "requirements.txt", "pyproject.toml"))],
        },
        "regressions": regressions,
        "missing_tests": missing_tests,
        "risks": list(dict.fromkeys([*regressions, *security_risks, *(missing_tests)]))[:12],
        "recommendations": recommendations or ["No blocking issues detected by allowlisted checks."],
        "impact_risk": impact.get("risk"),
    }
