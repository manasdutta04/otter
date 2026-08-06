"""Orchestrate pure-Python repository analysis."""
from __future__ import annotations

from pathlib import Path

from .auth import detect_auth
from .config import detect_config
from .database import detect_databases
from .frameworks import detect_frameworks
from .manifests import collect_dependencies, detect_package_managers
from .routes import detect_routes
from .scanner import language_counts, list_files
from .testing import detect_testing
from .types import FolderInfo, RepositoryAnalysis

ENTRY_NAMES = {
    "main.py",
    "app.py",
    "server.py",
    "index.ts",
    "index.tsx",
    "index.js",
    "main.ts",
    "main.tsx",
    "manage.py",
    "server/index.ts",
    "src/main.ts",
    "src/index.ts",
}

FOLDER_ROLES = {
    "app": "Application routes / UI",
    "apps": "Monorepo applications",
    "src": "Primary source",
    "server": "Backend / server",
    "client": "Frontend client",
    "shared": "Shared modules",
    "lib": "Libraries / utilities",
    "components": "UI components",
    "pages": "Pages router",
    "api": "API surface",
    "routes": "HTTP routes",
    "models": "Data models",
    "schema": "Schema definitions",
    "schemas": "Schema definitions",
    "migrations": "Database migrations",
    "tests": "Tests",
    "test": "Tests",
    "__tests__": "Tests",
    "docs": "Documentation",
    "scripts": "Scripts / tooling",
    "docker": "Container config",
    "public": "Static assets",
    "config": "Configuration",
}


def _folder_role(path: str) -> str:
    top = path.split("/")[0].lower()
    if top in FOLDER_ROLES:
        return FOLDER_ROLES[top]
    lower = path.lower()
    for key, role in FOLDER_ROLES.items():
        if f"/{key}/" in f"/{lower}/" or lower.endswith(f"/{key}"):
            return role
    return "source"


def analyze_repository(root: Path) -> RepositoryAnalysis:
    root = Path(root)
    files = list_files(root)
    langs = language_counts(files)
    languages = sorted(langs.keys(), key=lambda k: (-langs[k], k))
    managers = detect_package_managers(root, files)
    deps, scripts, dep_names = collect_dependencies(root)
    frameworks = detect_frameworks(files, dep_names, root)
    routes = detect_routes(root, files)
    databases = detect_databases(root, files, dep_names)
    auth = detect_auth(root, files, dep_names)
    config_files, ci, docker = detect_config(root, files)
    testing = detect_testing(files, dep_names, scripts)

    folder_counts: dict[str, int] = {}
    for path in files:
        if path.parent == root:
            continue
        folder = str(path.parent.relative_to(root)).replace("\\", "/")
        # top-level and one nested level for brevity
        top = "/".join(folder.split("/")[:2])
        folder_counts[top] = folder_counts.get(top, 0) + 1
    folders = [
        FolderInfo(path=path, role=_folder_role(path), file_count=count)
        for path, count in sorted(folder_counts.items(), key=lambda item: (-item[1], item[0]))[:40]
    ]

    entry_points: list[str] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        if path.name.lower() in {n.split("/")[-1].lower() for n in ENTRY_NAMES} or rel.lower() in {n.lower() for n in ENTRY_NAMES}:
            entry_points.append(rel)
    entry_points = sorted(set(entry_points))[:30]

    signals: list[str] = []
    if routes:
        signals.append(f"API routes detected ({len(routes)})")
    if databases:
        signals.append("Database / ORM surface detected")
    if auth:
        signals.append("Authentication surface detected")
    if testing:
        signals.append("Automated tests detected")
    if docker:
        signals.append("Containerized runtime detected")
    if ci:
        signals.append("CI configuration detected")

    facts: list[str] = [
        f"{len(files)} tracked files",
        f"Languages: {', '.join(languages[:6]) or 'unknown'}",
    ]
    if frameworks:
        facts.append("Frameworks: " + ", ".join(frameworks[:8]))
    if managers:
        facts.append("Package managers: " + ", ".join(managers))

    summary = "; ".join(facts) + "."

    return RepositoryAnalysis(
        summary_facts=facts,
        languages=languages,
        package_managers=managers,
        frameworks=frameworks,
        entry_points=entry_points,
        folders=folders,
        api_routes=routes,
        databases=databases,
        auth=auth,
        config_files=config_files,
        ci=ci,
        docker=docker,
        testing=testing,
        dependency_manifest=deps[:60],
        architecture_signals=signals,
        summary=summary,
    )


def analysis_to_legacy_dict(analysis: RepositoryAnalysis) -> dict[str, object]:
    """Shape expected by save_intelligence + older callers."""
    tech = sorted(set(analysis.languages + analysis.frameworks + analysis.package_managers))
    folder_paths = [f.path for f in analysis.folders]
    return {
        "summary": analysis.summary,
        "tech_stack": tech,
        "folders": folder_paths,
        "folders_rich": [f.__dict__ for f in analysis.folders],
        "entry_points": analysis.entry_points,
        "architecture_signals": analysis.architecture_signals,
        "analysis": analysis.to_dict(),
    }
