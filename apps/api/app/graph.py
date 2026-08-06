"""Architecture graph — imports, folders, manifests, auth/api links."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .models import RepositoryGraph

IGNORED = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv"}
IMPORT_PATTERNS = [
    re.compile(r"^\s*(?:from|import)\s+([\w./@-]+)", re.MULTILINE),
    re.compile(r"""(?:require|import)\(['"]([^'"]+)['"]\)"""),
    re.compile(r"""from\s+['"]([^'"]+)['"]"""),
]


def _load_tsconfig_paths(root: Path) -> dict[str, str]:
    """Map alias prefix → relative folder (best-effort)."""
    for name in ("tsconfig.json", "jsconfig.json"):
        path = root / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        paths = (data.get("compilerOptions") or {}).get("paths") or {}
        aliases: dict[str, str] = {}
        for key, values in paths.items():
            if not isinstance(values, list) or not values:
                continue
            target = str(values[0]).replace("/*", "").lstrip("./")
            prefix = str(key).replace("/*", "")
            aliases[prefix] = target
        if aliases:
            return aliases
    # Common Otter / Replit style
    return {"@shared": "shared", "@": "src"}


def _resolve_import(root: Path, source: Path, imported: str, files_by_stem: dict[str, list[Path]], aliases: dict[str, str]) -> Path | None:
    cleaned = imported.strip()
    if cleaned.startswith("."):
        base = (source.parent / cleaned).resolve()
        for candidate in (
            base,
            Path(str(base) + ".ts"),
            Path(str(base) + ".tsx"),
            Path(str(base) + ".js"),
            Path(str(base) + ".py"),
            base / "index.ts",
            base / "index.js",
        ):
            if candidate.is_file() and root in candidate.parents:
                return candidate
        return None
    for prefix, target in aliases.items():
        if cleaned == prefix or cleaned.startswith(prefix + "/"):
            rest = cleaned[len(prefix) :].lstrip("/")
            base = root / target / rest
            for candidate in (
                base,
                Path(str(base) + ".ts"),
                Path(str(base) + ".tsx"),
                Path(str(base) + ".js"),
                base / "index.ts",
            ):
                if candidate.is_file():
                    return candidate
    stem = cleaned.split("/")[-1]
    matches = files_by_stem.get(stem) or []
    if len(matches) == 1:
        return matches[0]
    return None


def build_graph(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    root = Path(root)
    files = [path for path in root.rglob("*") if path.is_file() and not any(part in IGNORED for part in path.parts)]
    aliases = _load_tsconfig_paths(root)
    files_by_stem: dict[str, list[Path]] = {}
    for path in files:
        files_by_stem.setdefault(path.stem, []).append(path)

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
        if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".py"}:
            imports: set[str] = set()
            for pattern in IMPORT_PATTERNS:
                imports.update(pattern.findall(content))
            for imported in imports:
                if imported.startswith(("http:", "https:", "node:")):
                    continue
                target = _resolve_import(root, path, imported, files_by_stem, aliases)
                if target:
                    target_relative = str(target.relative_to(root)).replace("\\", "/")
                    edges.append({"source": node_id, "target": f"file:{target_relative}", "kind": "imports"})
        if path.parent != root:
            folder = str(path.parent.relative_to(root)).replace("\\", "/")
            folder_id = f"folder:{folder}"
            nodes[folder_id] = {"id": folder_id, "label": path.parent.name, "kind": "folder", "path": folder}
            edges.append({"source": folder_id, "target": node_id, "kind": "contains"})

    # Manifest dependency edges (capped)
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            nodes["manifest:package.json"] = {
                "id": "manifest:package.json",
                "label": "package.json",
                "kind": "manifest",
                "path": "package.json",
            }
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            for name in list(deps.keys())[:40]:
                dep_id = f"dep:{name}"
                nodes[dep_id] = {"id": dep_id, "label": name, "kind": "dependency", "path": name}
                edges.append({"source": "manifest:package.json", "target": dep_id, "kind": "depends_on"})
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    # Auth / API flow edges (path heuristics)
    auth_files = [p for p in files if any(tok in str(p).lower() for tok in ("auth", "passport", "session", "login"))]
    route_files = [
        p
        for p in files
        if "route" in p.name.lower()
        or "routes" in str(p).lower()
        or (p.parent.name == "api" and p.name.startswith("route."))
    ]
    for route in route_files[:15]:
        route_rel = str(route.relative_to(root)).replace("\\", "/")
        for auth in auth_files[:10]:
            auth_rel = str(auth.relative_to(root)).replace("\\", "/")
            if route_rel == auth_rel:
                continue
            edges.append({"source": f"file:{route_rel}", "target": f"file:{auth_rel}", "kind": "api_flow"})

    unique_edges = list({(edge["source"], edge["target"], edge["kind"]): edge for edge in edges}.values())
    return list(nodes.values()), unique_edges


async def save_graph(db: AsyncSession, repository_id: str, nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> None:
    await db.merge(
        RepositoryGraph(
            repository_id=repository_id,
            nodes=json.dumps(nodes),
            edges=json.dumps(edges),
            generated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
