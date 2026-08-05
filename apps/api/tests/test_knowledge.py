from pathlib import Path
from app.analyzer import inspect_repository

def test_documentation_inputs_are_deterministic(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Example\n\nA useful service.", encoding="utf-8")
    result = inspect_repository(tmp_path)
    assert result["summary"] == "# Example"
