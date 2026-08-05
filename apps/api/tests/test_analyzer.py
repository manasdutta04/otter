from pathlib import Path
from app.analyzer import inspect_repository

def test_analyzer_detects_stack_and_entry_points(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.ts").write_text("export {}", encoding="utf-8")
    result = inspect_repository(tmp_path)
    assert "Node.js" in result["tech_stack"]
    assert "TypeScript" in result["tech_stack"]
    assert "src/main.ts" in result["entry_points"]
