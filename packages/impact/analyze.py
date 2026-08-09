"""Blast-radius and change-radar analysis on top of the import graph."""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from packages.planner import build_plan

from .graph import build_import_graph


def _normalize_focus(path: str) -> str:
    cleaned = path.replace("\\", "/").lstrip("./")
    if cleaned.startswith("file:"):
        return cleaned
    return f"file:{cleaned}"


def _adjacency(
    edges: list[dict[str, str]],
    *,
    reverse: bool = False,
) -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in edges:
        src, tgt, kind = edge["source"], edge["target"], edge.get("kind") or "related"
        if reverse:
            adj[tgt].append((src, kind))
        else:
            adj[src].append((tgt, kind))
    return adj


def _bfs(
    start: str,
    adj: dict[str, list[tuple[str, str]]],
    *,
    max_depth: int = 4,
    max_nodes: int = 40,
) -> list[dict[str, Any]]:
    seen = {start}
    queue: deque[tuple[str, int, str | None]] = deque([(start, 0, None)])
    out: list[dict[str, Any]] = []
    while queue and len(out) < max_nodes:
        node, depth, via = queue.popleft()
        if depth > 0:
            out.append({"id": node, "depth": depth, "via": via})
        if depth >= max_depth:
            continue
        for nxt, kind in adj.get(node, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append((nxt, depth + 1, kind))
    return out


def _risk_level(count: int, kinds: set[str]) -> str:
    if count >= 12 or "api_flow" in kinds:
        return "high"
    if count >= 5:
        return "medium"
    return "low"


def impact_from_focus(
    root: Path,
    *,
    focus_paths: list[str] | None = None,
    symbols: list[str] | None = None,
    depth: int = 3,
) -> dict[str, Any]:
    """What a change to focus paths would affect (forward + reverse import hops)."""
    root = Path(root)
    nodes, edges = build_import_graph(root)
    by_id = {n["id"]: n for n in nodes}
    fwd = _adjacency(edges, reverse=False)
    rev = _adjacency(edges, reverse=True)

    seeds: list[str] = []
    for path in focus_paths or []:
        seeds.append(_normalize_focus(path))
    if symbols:
        needle = [s.lower() for s in symbols]
        for node in nodes:
            if node.get("kind") != "file":
                continue
            label = (node.get("label") or "").lower()
            path = (node.get("path") or "").lower()
            if any(n in label or n in path for n in needle):
                seeds.append(node["id"])
    seeds = list(dict.fromkeys(seeds))
    if not seeds:
        return {
            "risk": "low",
            "affected_files": [],
            "affected_modules": [],
            "affected_apis": [],
            "affected_database_entities": [],
            "affected_tests": [],
            "architecture_boundaries": [],
            "risks": ["No focus path or symbol matched the repository graph."],
            "recommended_verification": ["Provide a concrete file path or symbol."],
            "seeds": [],
        }

    affected: dict[str, dict[str, Any]] = {}
    edge_kinds: set[str] = set()
    for seed in seeds:
        for item in _bfs(seed, fwd, max_depth=depth) + _bfs(seed, rev, max_depth=depth):
            nid = item["id"]
            if not nid.startswith("file:"):
                continue
            prev = affected.get(nid)
            if not prev or item["depth"] < prev["depth"]:
                affected[nid] = item
            if item.get("via"):
                edge_kinds.add(str(item["via"]))

    files = sorted(
        (
            {
                "path": by_id.get(nid, {}).get("path") or nid.removeprefix("file:"),
                "depth": meta["depth"],
                "direction": "related",
            }
            for nid, meta in affected.items()
        ),
        key=lambda x: (x["depth"], x["path"]),
    )[:40]

    modules = sorted(
        {
            "/".join(f["path"].split("/")[:2])
            for f in files
            if "/" in f["path"]
        }
    )[:20]
    tests = [f["path"] for f in files if "test" in f["path"].lower() or f["path"].endswith("_test.py")]
    apis = [f["path"] for f in files if any(t in f["path"].lower() for t in ("route", "api", "controller"))]
    db = [f["path"] for f in files if any(t in f["path"].lower() for t in ("model", "schema", "migration", "entity"))]

    risk = _risk_level(len(files), edge_kinds)
    risks = []
    if risk == "high":
        risks.append("Large blast radius across many modules.")
    if apis:
        risks.append("API/route surfaces may change behavior for clients.")
    if db:
        risks.append("Data layer files are in the impact set — check migrations and contracts.")
    if not tests:
        risks.append("No obvious test files in the impact set.")

    return {
        "risk": risk,
        "affected_files": files,
        "affected_modules": modules,
        "affected_apis": apis[:15],
        "affected_database_entities": db[:15],
        "affected_tests": tests[:15],
        "architecture_boundaries": [
            m for m in modules if any(tok in m.lower() for tok in ("auth", "db", "api", "ui", "web", "server"))
        ][:10],
        "risks": risks or ["Limited coupling detected for this focus."],
        "recommended_verification": [
            "Run targeted tests for affected modules",
            "Typecheck / lint the changed packages",
            "Manually exercise affected API routes if any",
        ],
        "seeds": [s.removeprefix("file:") for s in seeds],
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def dependency_impact(
    root: Path,
    *,
    target: str,
    depth: int = 3,
) -> dict[str, Any]:
    """What depends on a file, symbol stem, module folder, or npm dependency name."""
    root = Path(root)
    nodes, edges = build_import_graph(root)
    by_id = {n["id"]: n for n in nodes}
    rev = _adjacency(edges, reverse=True)

    target = target.strip().replace("\\", "/")
    seeds: list[str] = []
    if target.startswith("dep:") or target in {n["path"] for n in nodes if n.get("kind") == "dependency"}:
        dep_id = target if target.startswith("dep:") else f"dep:{target}"
        if dep_id in by_id:
            seeds.append(dep_id)
    elif any(n["id"] == f"folder:{target}" for n in nodes):
        seeds.append(f"folder:{target}")
    else:
        focus = _normalize_focus(target)
        if focus in by_id:
            seeds.append(focus)
        else:
            low = target.lower()
            for node in nodes:
                if node.get("kind") != "file":
                    continue
                if low in (node.get("path") or "").lower() or low in (node.get("label") or "").lower():
                    seeds.append(node["id"])

    seeds = list(dict.fromkeys(seeds))
    consumers: list[dict[str, Any]] = []
    for seed in seeds:
        for item in _bfs(seed, rev, max_depth=depth, max_nodes=50):
            if item["id"].startswith("file:"):
                consumers.append(
                    {
                        "path": by_id.get(item["id"], {}).get("path") or item["id"].removeprefix("file:"),
                        "depth": item["depth"],
                        "via": item.get("via"),
                    }
                )

    # unique by path
    uniq: dict[str, dict[str, Any]] = {}
    for c in consumers:
        prev = uniq.get(c["path"])
        if not prev or c["depth"] < prev["depth"]:
            uniq[c["path"]] = c
    consumers = sorted(uniq.values(), key=lambda x: (x["depth"], x["path"]))[:40]
    tests = [c["path"] for c in consumers if "test" in c["path"].lower()]
    apis = [c["path"] for c in consumers if any(t in c["path"].lower() for t in ("route", "api"))]
    risk = _risk_level(len(consumers), {str(c.get("via") or "") for c in consumers})

    return {
        "target": target,
        "seeds": [s.removeprefix("file:").removeprefix("dep:").removeprefix("folder:") for s in seeds],
        "risk": risk,
        "direct_consumers": [c for c in consumers if c["depth"] == 1][:20],
        "indirect_consumers": [c for c in consumers if c["depth"] > 1][:20],
        "affected_apis": apis[:15],
        "affected_tests": tests[:15],
        "recommended_checks": [
            "Search for remaining references after removal/rename",
            "Run tests that import the target",
            "Check public API / export surfaces",
        ],
    }


def change_radar(root: Path, request: str, intelligence: dict | None = None) -> dict[str, Any]:
    """Pre-implementation scope: plan + impact on likely files."""
    root = Path(root)
    plan = build_plan(root, request, intelligence)
    focus = list(plan.get("affected_files") or [])[:12]
    impact = impact_from_focus(root, focus_paths=focus, depth=3) if focus else impact_from_focus(
        root, symbols=request.lower().split()[:5], depth=2
    )
    return {
        "request": request,
        "estimated_complexity": plan.get("complexity"),
        "likely_scope": plan.get("summary"),
        "steps": plan.get("steps"),
        "likely_files": focus or [f["path"] for f in impact.get("affected_files", [])[:10]],
        "affected_modules": impact.get("affected_modules"),
        "dependency_changes": plan.get("dependencies"),
        "migration_implications": [
            d for d in (plan.get("dependencies") or []) if "migration" in str(d).lower() or "database" in str(d).lower()
        ],
        "api_implications": impact.get("affected_apis"),
        "test_implications": impact.get("affected_tests") or plan.get("dependencies"),
        "security_implications": [
            r for r in (plan.get("risks") or []) if any(t in str(r).lower() for t in ("token", "auth", "access", "secret"))
        ],
        "risk": impact.get("risk"),
        "risks": list(dict.fromkeys([*(plan.get("risks") or []), *(impact.get("risks") or [])])),
        "recommended_verification": impact.get("recommended_verification"),
    }
