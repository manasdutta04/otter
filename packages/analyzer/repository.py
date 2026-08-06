from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from ._shared import DEFAULT_IGNORED, MANIFESTS, contains_text
from packages.retrieval import RepositoryRetrievalIndex

@dataclass(frozen=True)
class RepositoryIntelligenceSnapshot:
    summary: str
    tech_stack: list[str]
    folders: list[str]
    entry_points: list[str]
    architecture_signals: list[str]


def inspect_repository(root: Path) -> RepositoryIntelligenceSnapshot:
    retrieval = RepositoryRetrievalIndex(root)
    files = retrieval.files
    names = {path.name for path in files}
    tech_stack = sorted({value for key, value in MANIFESTS.items() if key in names})
    if any(path.suffix in {".tsx", ".ts"} for path in files):
        tech_stack.append("TypeScript")
    if any(path.suffix == ".py" for path in files):
        tech_stack.append("Python")
    if any(path.name.lower() in {"dockerfile", "compose.yml", "docker-compose.yml"} for path in files):
        tech_stack.append("Docker")
    folders = retrieval.list_folders()
    entry_points = retrieval.list_entry_points()
    signals: list[str] = []
    if any("api" in part.lower() for path in files for part in path.parts):
        signals.append("API surface detected")
    if any("test" in part.lower() for path in files for part in path.parts):
        signals.append("Automated tests detected")
    if any(path.name.lower() in {"dockerfile", "compose.yml", "docker-compose.yml"} for path in files):
        signals.append("Containerized runtime detected")
    if contains_text(root, ["auth", "login", "session", "oauth", "jwt"]):
        signals.append("Authentication surface detected")
    if contains_text(root, ["plan", "planner", "roadmap"]):
        signals.append("Planning surface detected")
    readme = next((path for path in files if path.name.lower() in {"readme.md", "readme"}), None)
    readme_text = readme.read_text(encoding="utf-8", errors="ignore")[:4000] if readme else ""
    summary = readme_text.strip().split("\n\n")[0][:600] if readme_text.strip() else f"Repository contains {len(files)} files across {len(folders)} folders."
    return RepositoryIntelligenceSnapshot(summary=summary, tech_stack=sorted(set(tech_stack)), folders=folders, entry_points=entry_points, architecture_signals=signals)
