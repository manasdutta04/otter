from pathlib import Path
from app.planner import build_plan

def test_planner_identifies_auth_surfaces(tmp_path: Path):
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "middleware.py").write_text("", encoding="utf-8")
    plan = build_plan(tmp_path, "Add OAuth authentication", {"entry_points": []})
    assert plan["complexity"] in {"medium", "high"}
    assert "auth/middleware.py" in plan["affected_files"]
    assert plan["risks"]


def test_planner_affected_files_are_code_not_locale_or_license(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    locale = tmp_path / "docs" / "_locale" / "fr" / "LC_MESSAGES"
    locale.mkdir(parents=True)
    (locale / "api.po").write_text('msgid "api"\n', encoding="utf-8")
    (tmp_path / "starlette").mkdir()
    (tmp_path / "starlette" / "middleware").mkdir()
    (tmp_path / "starlette" / "middleware" / "base.py").write_text("class BaseHTTPMiddleware:\n    pass\n", encoding="utf-8")
    plan = build_plan(
        tmp_path,
        "Add a RequestIdMiddleware using the plugin API",
        {"entry_points": ["starlette/middleware/base.py"]},
    )
    affected = [str(p).replace("\\", "/") for p in plan["affected_files"]]
    assert affected
    assert all(not p.lower().endswith(".po") for p in affected)
    assert all("license" not in p.lower() for p in affected)
    assert any(p.endswith(".py") for p in affected)
