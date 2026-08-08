from pathlib import Path
from app.analyzer import inspect_repository

def test_documentation_inputs_are_deterministic(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Example\n\nA useful service.", encoding="utf-8")
    result = inspect_repository(tmp_path)
    summary = result["summary"]
    assert isinstance(summary, str) and summary
    # Summary is a deterministic inventory line (not the README H1).
    assert "Markdown" in summary
    assert "1 tracked" in summary or "tracked files" in summary
