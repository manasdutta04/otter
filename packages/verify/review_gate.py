"""Compose impact + guard + verify into PASS / REVIEW / BLOCKED."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.architecture import guard_proposal
from packages.impact import change_radar

from .verify import verify_repository


def review_gate(
    root: Path,
    *,
    objective: str,
    proposal: str | None = None,
    focus_paths: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(root)
    radar = change_radar(root, objective)
    guard = guard_proposal(
        root,
        proposal=proposal or objective,
        target_paths=focus_paths or list(radar.get("likely_files") or [])[:12],
    )
    verification = verify_repository(
        root,
        proposal=proposal or objective,
        focus_paths=focus_paths or list(radar.get("likely_files") or [])[:12],
    )

    reasons: list[str] = []
    required: list[str] = []
    if guard.get("status") == "fail":
        for v in guard.get("violations") or []:
            reasons.append(v.get("rule") or "Architecture violation")
            required.append(v.get("recommended_alternative") or "Align with repository constitution")
    if verification.get("verdict") == "blocked":
        reasons.extend(verification.get("risks") or ["Verification blocked"])
        required.extend(verification.get("recommendations") or [])
    elif verification.get("verdict") == "review":
        reasons.extend(verification.get("missing_tests") or verification.get("risks") or ["Needs human review"])
        required.extend(verification.get("recommendations") or [])

    if verification.get("verdict") == "blocked" or guard.get("status") == "fail":
        verdict = "BLOCKED"
    elif verification.get("verdict") == "review" or radar.get("risk") == "high":
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "reasons": reasons[:12],
        "required_actions": list(dict.fromkeys(required))[:12],
        "radar": {
            "risk": radar.get("risk"),
            "likely_files": radar.get("likely_files"),
            "complexity": radar.get("estimated_complexity"),
        },
        "guard": guard,
        "verification": {
            "verdict": verification.get("verdict"),
            "tests": verification.get("tests"),
            "typecheck": verification.get("typecheck"),
            "lint": verification.get("lint"),
            "build": verification.get("build"),
            "security": verification.get("security"),
        },
    }
