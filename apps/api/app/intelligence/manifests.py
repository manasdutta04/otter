"""Manifest / package-manager detection."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .scanner import read_text_capped
from .types import DependencyInfo


def detect_package_managers(root: Path, files: list[Path]) -> list[str]:
    names = {path.name.lower() for path in files}
    managers: list[str] = []
    if "package.json" in names:
        managers.append("npm")
        if "pnpm-lock.yaml" in names:
            managers.append("pnpm")
        if "yarn.lock" in names:
            managers.append("yarn")
        if "bun.lockb" in names or "bun.lock" in names:
            managers.append("bun")
    if "requirements.txt" in names or "pyproject.toml" in names or "Pipfile" in names:
        managers.append("pip")
    if "poetry.lock" in names:
        managers.append("poetry")
    if "go.mod" in names:
        managers.append("go")
    if "Cargo.toml" in names:
        managers.append("cargo")
    return sorted(set(managers))


def _parse_package_json(root: Path) -> tuple[list[DependencyInfo], dict[str, str], dict]:
    path = root / "package.json"
    if not path.is_file():
        return [], {}, {}
    try:
        data = json.loads(read_text_capped(path, 200_000))
    except json.JSONDecodeError:
        return [], {}, {}
    deps: list[DependencyInfo] = []
    merged: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(section) or {}
        if isinstance(block, dict):
            for name, version in block.items():
                merged[str(name)] = str(version)
    for name, version in sorted(merged.items())[:80]:
        deps.append(DependencyInfo(name=name, version=version))
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    return deps, {str(k): str(v) for k, v in scripts.items()}, data


def _parse_requirements(root: Path) -> list[DependencyInfo]:
    path = root / "requirements.txt"
    if not path.is_file():
        return []
    deps: list[DependencyInfo] = []
    for line in read_text_capped(path, 50_000).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.\-]+)\s*([=<>!~].+)?", line)
        if match:
            deps.append(DependencyInfo(name=match.group(1), version=(match.group(2) or "").strip() or "*"))
        if len(deps) >= 80:
            break
    return deps


def _parse_pyproject(root: Path) -> list[DependencyInfo]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return []
    text = read_text_capped(path, 80_000)
    deps: list[DependencyInfo] = []
    for match in re.finditer(r'^\s*"?([A-Za-z0-9_.\-]+)"?\s*[>=<~!]=?\s*"?([^"\s,]+)"?', text, re.MULTILINE):
        name = match.group(1)
        if name in {"python", "requires-python"}:
            continue
        deps.append(DependencyInfo(name=name, version=match.group(2)))
        if len(deps) >= 80:
            break
    return deps


def collect_dependencies(root: Path) -> tuple[list[DependencyInfo], dict[str, str], set[str]]:
    """Return deps, npm scripts, and flat dependency name set."""
    npm_deps, scripts, _ = _parse_package_json(root)
    py_deps = _parse_requirements(root) + _parse_pyproject(root)
    all_deps = npm_deps + py_deps
    names = {item.name.lower() for item in all_deps}
    # Deduplicate by name keeping first
    seen: set[str] = set()
    unique: list[DependencyInfo] = []
    for item in all_deps:
        key = item.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:100], scripts, names
