from pathlib import Path
from app.performance import PATTERNS
from app.architecture_analysis import analyze_architecture

def test_phase4_analyzers_define_transparent_rules(tmp_path: Path):
    assert PATTERNS
    assert callable(analyze_architecture)
