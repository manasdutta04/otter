"""Targeted repository understanding for MCP."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.impact import build_import_graph, impact_from_focus
from packages.retrieval import answer_repository_question


def understand_repository(
    root: Path,
    task: str,
    *,
    focus_path: str | None = None,
    symbols: list[str] | None = None,
    depth: int = 2,
) -> dict[str, Any]:
    root = Path(root)
    qa = answer_repository_question(root, task)
    focus = [focus_path] if focus_path else []
    if not focus:
        focus = [c.get("path") for c in (qa.get("contexts") or [])[:5] if c.get("path")]
    impact = impact_from_focus(root, focus_paths=[p for p in focus if p], symbols=symbols, depth=depth)
    nodes, edges = build_import_graph(root)
    file_nodes = [n for n in nodes if n.get("kind") == "file"][:30]

    # light conventions from paths
    conventions: list[str] = []
    paths = " ".join(n.get("path") or "" for n in file_nodes).lower()
    if "auth" in paths:
        conventions.append("Auth-related modules present")
    if any(p.endswith(".tsx") or p.endswith(".jsx") for p in (n.get("path") or "" for n in file_nodes)):
        conventions.append("Frontend UI files present (tsx/jsx)")
    if any("test" in (n.get("path") or "").lower() for n in file_nodes):
        conventions.append("Test files present")

    sources = (qa.get("sources") or [])[:8]
    return {
        "task": task,
        "summary": (qa.get("answer") or "")[:1500],
        "architecture_signals": {
            "file_count_sampled": len(file_nodes),
            "edge_count": len(edges),
            "modules": impact.get("affected_modules") or [],
        },
        "relevant_files": [
            {"path": s.get("path"), "start_line": s.get("start_line"), "end_line": s.get("end_line")}
            for s in sources
        ],
        "relevant_symbols": symbols or [],
        "dependencies": impact.get("affected_apis") or [],
        "relationships": [
            {"path": f.get("path"), "depth": f.get("depth")} for f in (impact.get("affected_files") or [])[:12]
        ],
        "conventions": conventions,
        "related_tests": impact.get("affected_tests") or [],
        "citations": sources,
        "risk": impact.get("risk"),
    }
