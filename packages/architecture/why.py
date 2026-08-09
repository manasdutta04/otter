"""Explain why a file/symbol exists using retrieval + graph + optional git."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from packages.impact import dependency_impact
from packages.retrieval import answer_repository_question


def explain_why(root: Path, subject: str, *, max_commits: int = 5) -> dict[str, Any]:
    root = Path(root)
    subject = subject.strip()
    retrieval = answer_repository_question(root, f"what is {subject} and why does it exist?")
    impact = dependency_impact(root, target=subject, depth=2)

    commits: list[dict[str, str]] = []
    git = root / ".git"
    if git.exists():
        try:
            result = subprocess.run(
                ["git", "log", f"-n{max_commits}", "--oneline", "--", subject],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(" ", 1)
                    commits.append({"sha": parts[0], "message": parts[1] if len(parts) > 1 else ""})
        except (OSError, subprocess.TimeoutExpired):
            commits = []

    confidence = "medium"
    if not retrieval.get("sources") and not commits and not impact.get("direct_consumers"):
        confidence = "low"
    elif retrieval.get("sources") and (commits or impact.get("direct_consumers")):
        confidence = "high"

    what = retrieval.get("answer") or ""
    if confidence == "low":
        what = (
            f"Could not determine a confident historical reason for `{subject}` "
            "from retrieval, consumers, or git history."
        )

    return {
        "subject": subject,
        "what_it_does": what[:1200],
        "consumers": impact.get("direct_consumers") or [],
        "related_code": (retrieval.get("sources") or [])[:5],
        "commits": commits,
        "consequences_of_removal": [
            f"{len(impact.get('direct_consumers') or [])} direct consumer(s) may break",
            *([f"APIs: {', '.join(impact.get('affected_apis') or [])}"] if impact.get("affected_apis") else []),
        ],
        "confidence": confidence,
        "fabricated": False,
    }
