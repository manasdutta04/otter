import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryIntelligence

IGNORED = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv"}
MANIFESTS = {"package.json": "Node.js", "requirements.txt": "Python", "pyproject.toml": "Python", "go.mod": "Go", "Cargo.toml": "Rust", "pom.xml": "Java", "docker-compose.yml": "Docker"}

def inspect_repository(root: Path) -> dict[str, object]:
    files = [path for path in root.rglob("*") if path.is_file() and not any(part in IGNORED for part in path.parts)]
    names = {path.name for path in files}
    tech_stack = sorted({value for key, value in MANIFESTS.items() if key in names})
    if any(path.suffix in {".tsx", ".ts"} for path in files): tech_stack.append("TypeScript")
    if any(path.suffix == ".py" for path in files): tech_stack.append("Python")
    if any(path.name.lower() in {"dockerfile", "compose.yml", "docker-compose.yml"} for path in files): tech_stack.append("Docker")
    folders = sorted({str(path.parent.relative_to(root)).replace("\\", "/") for path in files if path.parent != root})[:80]
    entry_points = [str(path.relative_to(root)).replace("\\", "/") for path in files if path.name.lower() in {"main.py", "app.py", "server.py", "index.ts", "index.tsx", "main.ts", "main.tsx", "manage.py"}][:30]
    signals = []
    if any("api" in part.lower() for path in files for part in path.parts): signals.append("API surface detected")
    if any("test" in part.lower() for path in files for part in path.parts): signals.append("Automated tests detected")
    if any(path.name.lower() in {"dockerfile", "compose.yml", "docker-compose.yml"} for path in files): signals.append("Containerized runtime detected")
    readme = next((path for path in files if path.name.lower() in {"readme.md", "readme"}), None)
    readme_text = readme.read_text(encoding="utf-8", errors="ignore")[:4000] if readme else ""
    summary = readme_text.strip().split("\n\n")[0][:600] if readme_text.strip() else f"Repository contains {len(files)} files across {len(folders)} folders."
    return {"summary": summary, "tech_stack": sorted(set(tech_stack)), "folders": folders, "entry_points": entry_points, "architecture_signals": signals}

async def save_intelligence(db: AsyncSession, repository_id: str, data: dict[str, object]) -> None:
    record = RepositoryIntelligence(repository_id=repository_id, summary=str(data["summary"]), tech_stack=json.dumps(data["tech_stack"]), folders=json.dumps(data["folders"]), entry_points=json.dumps(data["entry_points"]), architecture_signals=json.dumps(data["architecture_signals"]), analyzed_at=datetime.now(timezone.utc))
    await db.merge(record)
    await db.commit()
