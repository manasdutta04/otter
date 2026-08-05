from pathlib import Path
from app.review import review_repository
def test_review_detects_todo_marker(tmp_path: Path):
    (tmp_path / "main.py").write_text("# TODO: simplify this", encoding="utf-8")
    assert review_repository(tmp_path)[0]["category"] == "maintainability"
