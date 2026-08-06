from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from packages.retrieval import RepositoryRetrievalIndex

IMPORT_PATTERNS = [re.compile(r"^\s*(?:from|import)\s+([\w./-]+)", re.MULTILINE), re.compile(r"(?:require|import)\(['\"]([^'\"]+)['\"]\)")]

@dataclass(frozen=True)
class GraphSnapshot:
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]


def build_graph(root: Path) -> GraphSnapshot:
    retrieval = RepositoryRetrievalIndex(root)
    files = retrieval.files
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
    return GraphSnapshot(nodes=list(nodes.values()), edges=unique_edges)
