from pathlib import Path
from app.graph import build_graph

def test_graph_extracts_import_edges(tmp_path: Path):
    (tmp_path / "main.py").write_text("from auth import login", encoding="utf-8")
    (tmp_path / "auth.py").write_text("def login(): pass", encoding="utf-8")
    nodes, edges = build_graph(tmp_path)
    assert any(node["path"] == "main.py" for node in nodes)
    assert any(edge["source"] == "file:main.py" and edge["target"] == "file:auth.py" for edge in edges)
