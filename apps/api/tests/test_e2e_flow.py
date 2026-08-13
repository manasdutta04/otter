import sys
from pathlib import Path

# Resolve monorepo (or Docker /workspace) root so packages.* imports work.
_here = Path(__file__).resolve()
REPO_ROOT = next(
    (
        parent
        for parent in _here.parents
        if (parent / "packages").is_dir()
        and ((parent / "apps").is_dir() or (parent / "app").is_dir())
    ),
    _here.parents[min(1, len(_here.parents) - 1)],
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from packages.retrieval import answer_repository_question, RepositorySemanticIndex
from packages.analyzer import inspect_repository
from packages.planner import build_plan
from packages.review import review_repository
from packages.health import analyze_health


def test_retrieval_ranks_source_above_package_json(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name":"app","dependencies":{"express":"4"}}\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.ts").write_text("export function requireAuth() { return true }\n", encoding="utf-8")
    (src / "readme-notes.md").write_text("authentication overview\n", encoding="utf-8")
    index = RepositorySemanticIndex(tmp_path)
    hits = index.search("Where is HTTP request authentication enforced?", top_k=5)
    ranked = [hit["rel_path"].replace("\\", "/") for hit in hits]
    assert ranked
    assert ranked[0].endswith("auth.ts")
    assert "package.json" not in ranked[:2]


def test_retrieval_literal_path_boosts_named_source(tmp_path: Path):
    (tmp_path / "bottle.py").write_text("def tob(x): return x\n", encoding="utf-8")
    tests = tmp_path / "test"
    tests.mkdir()
    for name in ("test_html_helper.py", "test_app.py", "test_plugins.py", "test_formsdict.py"):
        (tests / name).write_text("from bottle import tob\n", encoding="utf-8")
    index = RepositorySemanticIndex(tmp_path)
    hits = index.search(
        "Add a helper function is_valid_email(value) to bottle.py. Add a unittest in test/test_html_helper.py.",
        top_k=5,
    )
    ranked = [hit["rel_path"].replace("\\", "/") for hit in hits]
    assert "bottle.py" in ranked[:3]


def test_full_retrieval_and_semantic_chat(tmp_path: Path):
    # Setup dummy repo structure
    src = tmp_path / "src"
    src.mkdir()
    auth_file = src / "auth.py"
    auth_file.write_text("def authenticate_user(token):\n    '''Validate JWT authentication token.'''\n    return token == 'valid_secret'\n", encoding="utf-8")
    
    # Test semantic retrieval
    res = answer_repository_question(tmp_path, "where is authentication token validation?")
    assert len(res["sources"]) > 0
    assert "auth.py" in res["sources"][0]["path"]
    assert "authenticate_user" in res["answer"]

def test_end_to_end_analysis_planner_review(tmp_path: Path):
    # Test repository inspection
    intel = inspect_repository(tmp_path)
    assert "summary" in intel
    assert isinstance(intel["tech_stack"], list)

    # Test planner
    plan = build_plan(tmp_path, "Add OAuth authentication flow", intel)
    assert str(plan["complexity"]).lower() in {"low", "medium", "high"}
    assert len(plan["steps"]) > 0

    # Test review
    review = review_repository(tmp_path)
    assert "scores" in review
    assert len(review["issues"]) > 0

    # Test health
    health = analyze_health(tmp_path)
    assert health["status"] == "Healthy"
    assert health["score"] >= 80
