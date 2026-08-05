import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryGraph

IGNORED = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv"}
IMPORT_PATTERNS = [re.compile(r"^\s*(?:from|import)\s+([\w./-]+)", re.MULTILINE), re.compile(r"(?:require|import)\(['\"]([^'\"]+)['\"]\)")]

def build_graph(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    files = [path for path in root.rglob("*") if path.is_file() and not any(part in IGNORED for part in path.parts)]
    nodes: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []
    for path in files:
        relative = str(path.relative_to(root)).replace("\\", "/")
        node_id = f"file:{relative}"
        nodes[node_id] = {"id": node_id, "label": path.name, "kind": "file", "path": relative}
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:200000]
        except OSError:
            continue
        imports: set[str] = set()
        for pattern in IMPORT_PATTERNS:
            imports.update(pattern.findall(content))
        for imported in imports:
            target = next((candidate for candidate in files if candidate.stem == imported.split("/")[-1] or candidate.name == imported.split("/")[-1]), None)
            if target:
                target_relative = str(target.relative_to(root)).replace("\\", "/")
                edges.append({"source": node_id, "target": f"file:{target_relative}", "kind": "imports"})
        if path.parent != root:
            folder = str(path.parent.relative_to(root)).replace("\\", "/")
            folder_id = f"folder:{folder}"
            nodes[folder_id] = {"id": folder_id, "label": path.parent.name, "kind": "folder", "path": folder}
            edges.append({"source": folder_id, "target": node_id, "kind": "contains"})
    unique_edges = list({(edge["source"], edge["target"], edge["kind"]): edge for edge in edges}.values())
    return list(nodes.values()), unique_edges

async def save_graph(db: AsyncSession, repository_id: str, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> None:
    await db.merge(RepositoryGraph(repository_id=repository_id, nodes=json.dumps(nodes), edges=json.dumps(edges), generated_at=datetime.now(timezone.utc)))
    await db.commit()
