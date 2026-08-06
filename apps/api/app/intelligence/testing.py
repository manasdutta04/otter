"""Test framework detection."""
from __future__ import annotations

from pathlib import Path


def detect_testing(files: list[Path], dep_names: set[str], scripts: dict[str, str]) -> list[str]:
    found: list[str] = []
    if "jest" in dep_names or any("jest" in s for s in scripts.values()):
        found.append("jest")
    if "vitest" in dep_names:
        found.append("vitest")
    if "mocha" in dep_names:
        found.append("mocha")
    if "pytest" in dep_names or any(p.name in {"pytest.ini", "conftest.py"} for p in files):
        found.append("pytest")
    if "playwright" in dep_names or "@playwright/test" in dep_names:
        found.append("playwright")
    if "cypress" in dep_names:
        found.append("cypress")
    if any("test" in p.name.lower() or p.name.endswith((".test.ts", ".spec.ts", ".test.js", ".spec.js")) for p in files):
        if "test-files" not in found:
            found.append("test-files-present")
    script_blob = " ".join(scripts.keys()).lower()
    if "test" in script_blob and "npm-test-script" not in found:
        found.append("npm-test-script")
    return sorted(set(found))
