"""
Repository structural and architectural analysis package.
"""
from pathlib import Path
import json

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build"}

def inspect_repository(repo_root: Path) -> dict:
    """Analyze repository entry points, frameworks, tech stack, and structure."""
    file_count = 0
    folders = set()
    entry_points = []
    tech_stack = set()

    for p in repo_root.rglob("*"):
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.is_file():
            file_count += 1
            rel_p = p.relative_to(repo_root).as_posix()
            if p.parent != repo_root:
                folders.add(p.relative_to(repo_root).parts[0])
            
            # Detect tech stack & entry points
            if p.name == "package.json":
                tech_stack.add("Node.js / TypeScript")
            elif p.name == "pyproject.toml" or p.name == "requirements.txt":
                tech_stack.add("Python")
            elif p.name == "Dockerfile" or p.name == "docker-compose.yml":
                tech_stack.add("Docker")
            
            if p.name in {"main.py", "app.py", "server.py", "index.ts", "extension.ts", "server.ts", "page.tsx"}:
                entry_points.append(rel_p)

    if not tech_stack:
        tech_stack.add("Polyglot / Generic")

    summary = f"Repository contains {file_count} files across {len(folders)} top-level directories."
    architecture_signals = [
        f"Primary tech stack detected: {', '.join(sorted(tech_stack))}",
        f"Found {len(entry_points)} key entry point files.",
        f"Top-level structure: {', '.join(sorted(folders))}"
    ]

    return {
        "summary": summary,
        "tech_stack": sorted(tech_stack),
        "folders": sorted(folders),
        "entry_points": entry_points,
        "architecture_signals": architecture_signals
    }
