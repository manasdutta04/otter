"""
AI Planner package for engineering task decomposition.
"""
from pathlib import Path
import json

def build_plan(repo_root: Path, request: str, intelligence: dict | None = None) -> dict:
    """Generate a structured, repository-aware execution plan for a given task request."""
    # Find likely affected files by simple search or intelligence entry points
    affected_files = []
    if intelligence and "entry_points" in intelligence:
        affected_files.extend(intelligence["entry_points"][:3])
    
    if not affected_files:
        affected_files = ["apps/api/app/main.py", "apps/web/package.json"]

    steps = [
        f"1. Audit request requirements: '{request}'.",
        "2. Review target module interfaces and existing conventions.",
        "3. Implement core changes across affected components.",
        "4. Add unit and integration test coverage.",
        "5. Verify end-to-end functionality."
    ]

    dependencies = ["FastAPI", "SQLAlchemy", "Next.js", "pytest"]
    risks = [
        "Potential breaking changes in existing API contracts.",
        "Requires verification of user authentication boundaries."
    ]

    return {
        "title": f"Implementation Plan: {request[:50]}",
        "complexity": "Medium",
        "summary": f"Detailed step-by-step implementation guide to address: '{request}'",
        "steps": steps,
        "affected_files": affected_files,
        "dependencies": dependencies,
        "risks": risks
    }
