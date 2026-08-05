from pathlib import Path
from app.planner import build_plan

def test_planner_identifies_auth_surfaces(tmp_path: Path):
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "middleware.py").write_text("", encoding="utf-8")
    plan = build_plan(tmp_path, "Add OAuth authentication", {"entry_points": []})
    assert plan["complexity"] in {"medium", "high"}
    assert "auth/middleware.py" in plan["affected_files"]
    assert plan["risks"]
