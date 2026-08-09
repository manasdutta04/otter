"""Allowlisted validation commands — no arbitrary shell."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

ALLOWED_NPM_SCRIPTS = ("test", "lint", "typecheck", "build", "check")


def _run(cmd: list[str], cwd: Path, timeout: int = 180, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    exe = shutil.which(cmd[0])
    if not exe:
        return {"status": "skipped", "passed": None, "output": f"{cmd[0]} not available on PATH"}
    try:
        result = subprocess.run(
            [exe, *cmd[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-4000:]
        return {
            "status": "pass" if result.returncode == 0 else "fail",
            "passed": result.returncode == 0,
            "output": output,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"status": "fail", "passed": False, "output": "Command timed out", "command": " ".join(cmd)}
    except OSError as error:
        return {"status": "fail", "passed": False, "output": str(error), "command": " ".join(cmd)}


def _package_scripts(root: Path) -> dict[str, str]:
    pkg = root / "package.json"
    if not pkg.is_file():
        return {}
    try:
        data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts") or {}
    return {k: str(v) for k, v in scripts.items() if isinstance(v, str)}


def run_allowlisted_checks(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    results: dict[str, dict[str, Any]] = {}
    scripts = _package_scripts(root)

    if scripts:
        for name in ALLOWED_NPM_SCRIPTS:
            if name in scripts:
                results[name] = _run(["npm", "run", name, "--if-present"], root, timeout=240)
        if "test" not in results and "test" not in scripts:
            results["test"] = {
                "status": "skipped",
                "passed": None,
                "output": "No npm test script",
            }
    else:
        # Python
        if (root / "pyproject.toml").is_file() or any(root.glob("**/test_*.py")):
            results["test"] = _run(["python", "-m", "pytest", "-q", "--tb=line"], root, timeout=240)
        if shutil.which("ruff"):
            results["lint"] = _run(["ruff", "check", "."], root, timeout=120)

    return results


def run_repository_tests(root: Path) -> dict[str, Any]:
    """Shared Node/pytest test runner used by API code-tasks and MCP verify."""
    root = Path(root)
    package_json = root / "package.json"
    if package_json.is_file():
        npm = shutil.which("npm")
        if not npm:
            return {
                "passed": False,
                "output": (
                    "This repository looks like a Node project, but `npm` is not available. "
                    "Install Node or run tests locally / via CI."
                ),
            }
        install_log = ""
        try:
            lockfile = root / "package-lock.json"
            install_cmd = [npm, "ci"] if lockfile.is_file() else [npm, "install", "--no-audit", "--no-fund"]
            install = subprocess.run(
                install_cmd,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=240,
            )
            install_log = ((install.stdout or "") + "\n" + (install.stderr or ""))[-6000:]
            if install.returncode != 0 and install_cmd[1] == "ci":
                install = subprocess.run(
                    [npm, "install", "--no-audit", "--no-fund"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=240,
                )
                install_log = ((install.stdout or "") + "\n" + (install.stderr or ""))[-6000:]
            if install.returncode != 0:
                return {"passed": False, "output": f"npm install failed:\n{install_log}"}
            scripts = _package_scripts(root)
            if "test" not in scripts:
                return {
                    "passed": False,
                    "output": (
                        "Dependencies installed, but package.json has no `test` script. "
                        "Add a test script or rely on CI for verification.\n"
                        f"{install_log[-2000:]}"
                    ),
                }
            result = subprocess.run(
                [npm, "test", "--", "--watchAll=false"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
                env={**os.environ, "CI": "true"},
            )
            output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:]
            return {"passed": result.returncode == 0, "output": output or "npm test finished with no output"}
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"passed": False, "output": f"npm test could not run: {error}\n{install_log}"}

    try:
        probe = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if probe.returncode != 0:
            return {
                "passed": False,
                "output": "No test runner detected (no package.json test script / pytest unavailable). Use local tests or CI.",
            }
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:]
        return {"passed": result.returncode == 0, "output": output}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"passed": False, "output": str(error)}
