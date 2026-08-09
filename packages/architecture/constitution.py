"""Infer a repository constitution from filesystem evidence (not hardcoded rules)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _has_any(root: Path, names: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        low = rel.lower()
        if any(n in low for n in names):
            found.append(rel)
            if len(found) >= 12:
                break
    return found


def build_constitution(root: Path, intelligence: dict | None = None) -> dict[str, Any]:
    root = Path(root)
    intel = intelligence or {}
    evidence: dict[str, list[str]] = {}

    pkg = root / "package.json"
    pyproject = root / "pyproject.toml"
    req = root / "requirements.txt"
    orm: list[str] = []
    deps: dict[str, str] = {}
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            for name in deps:
                low = name.lower()
                if any(t in low for t in ("drizzle", "prisma", "typeorm", "sequelize", "mongoose", "knex")):
                    orm.append(name)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    if pyproject.is_file() or req.is_file():
        text = ""
        try:
            text = (pyproject.read_text(encoding="utf-8", errors="ignore") if pyproject.is_file() else "") + (
                req.read_text(encoding="utf-8", errors="ignore") if req.is_file() else ""
            )
        except OSError:
            pass
        for name in ("sqlalchemy", "django", "tortoise", "prisma"):
            if name in text.lower():
                orm.append(name)

    routes = _has_any(root, ("route", "routes", "controller", "api/"))
    services = _has_any(root, ("service", "services", "usecase", "application/"))
    repos = _has_any(root, ("repository", "repositories", "dal", "infra/"))
    auth = _has_any(root, ("auth", "session", "passport", "middleware"))
    tests = _has_any(root, ("test", "spec", "__tests__"))
    evidence["routes"] = routes
    evidence["services"] = services
    evidence["repositories"] = repos
    evidence["authentication"] = auth
    evidence["tests"] = tests

    layers: list[str] = []
    if routes:
        layers.append("routes/controllers")
    if services:
        layers.append("services")
    if repos:
        layers.append("repositories/data-access")
    preferred_flow = " → ".join(layers) if len(layers) >= 2 else "unclear — follow existing folder patterns"

    forbidden: list[dict[str, str]] = []
    if services and repos:
        forbidden.append(
            {
                "pattern": "Database access directly inside route handlers when services/repositories exist",
                "reason": "Repository evidence shows separated service/repository layers.",
                "evidence": ",".join((services[:2] + repos[:2])),
            }
        )
    if len(orm) > 1:
        forbidden.append(
            {
                "pattern": f"Introducing an additional ORM alongside {orm[0]}",
                "reason": "Multiple ORMs increase inconsistency risk.",
                "evidence": ", ".join(orm),
            }
        )

    preferred: list[str] = []
    if orm:
        preferred.append(f"Use existing ORM/data stack: {', '.join(orm)}")
    if auth:
        preferred.append("Extend existing auth/session middleware rather than a parallel auth path")
    if tests:
        preferred.append("Add or update tests next to existing test layout")

    stack = list(intel.get("tech_stack") or [])
    if not stack and deps:
        stack = list(deps.keys())[:12]

    return {
        "architecture": {
            "preferred_flow": preferred_flow,
            "layers_detected": layers,
            "entry_points": list(intel.get("entry_points") or [])[:12],
        },
        "database": {"orm_or_clients": orm, "evidence": evidence.get("repositories", [])[:6]},
        "authentication": {"files": auth[:8], "guidance": preferred[1] if len(preferred) > 1 else "Follow existing auth files"},
        "api_conventions": {"route_files": routes[:8]},
        "frontend_conventions": {
            "signals": [s for s in stack if any(t in str(s).lower() for t in ("react", "next", "vue", "svelte"))]
        },
        "testing_conventions": {"test_files": tests[:8]},
        "error_handling": {"guidance": "Match existing try/catch and error middleware patterns in nearby modules"},
        "dependency_conventions": {
            "package_managers": ["npm"] if pkg.is_file() else (["pip"] if req.is_file() or pyproject.is_file() else []),
            "notable_dependencies": list(deps.keys())[:20],
        },
        "naming_conventions": {"guidance": "Mirror sibling file naming in the target folder"},
        "security_conventions": {
            "guidance": "Do not commit secrets; reuse existing auth boundaries",
            "auth_files": auth[:5],
        },
        "forbidden_patterns": forbidden,
        "preferred_patterns": preferred,
        "evidence": evidence,
        "tech_stack": stack[:20],
    }
