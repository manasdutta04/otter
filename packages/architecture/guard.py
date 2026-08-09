"""Architecture guard — compare a proposal against inferred constitution."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constitution import build_constitution

_DB_IN_ROUTE = re.compile(
    r"(prisma\.|drizzle\(|db\.|session\.query|sqlalchemy|pg\.query|knex\()",
    re.IGNORECASE,
)


def guard_proposal(
    root: Path,
    *,
    proposal: str,
    target_paths: list[str] | None = None,
    intelligence: dict | None = None,
) -> dict[str, Any]:
    root = Path(root)
    constitution = build_constitution(root, intelligence)
    violations: list[dict[str, str]] = []
    proposal_l = proposal.lower()
    paths = [p.replace("\\", "/") for p in (target_paths or [])]

    layers = constitution.get("architecture", {}).get("layers_detected") or []
    has_service = "services" in layers
    has_repo = any("repositor" in x for x in layers)

    # Route + DB anti-pattern
    if has_service and has_repo:
        route_like = any(any(t in p.lower() for t in ("route", "controller", "api/")) for p in paths) or any(
            t in proposal_l for t in ("route handler", "in the route", "express.get", "fastapi")
        )
        db_in_route_intent = bool(_DB_IN_ROUTE.search(proposal)) or any(
            t in proposal_l
            for t in ("sql in route", "query in handler", "prisma in route", "db in the route", "queries directly in")
        ) or (
            any(t in proposal_l for t in ("prisma", "drizzle", "sqlalchemy", "knex", "mongoose"))
            and any(t in proposal_l for t in ("route handler", "in the route", "in route", "controller"))
        )
        if route_like and db_in_route_intent:
            violations.append(
                {
                    "rule": "Respect service/repository layering",
                    "evidence": constitution["architecture"]["preferred_flow"],
                    "why": "Routes reaching the database bypass established service boundaries.",
                    "recommended_alternative": "Put data access in repository/DAL and call it from a service used by the route.",
                }
            )

    orms = constitution.get("database", {}).get("orm_or_clients") or []
    if orms:
        rivals = {
            "prisma": ["typeorm", "sequelize", "mongoose"],
            "drizzle": ["prisma", "typeorm", "sequelize"],
            "sqlalchemy": ["django.db", "tortoise"],
        }
        primary = orms[0].lower()
        for key, others in rivals.items():
            if key in primary:
                for other in others:
                    if other in proposal_l and other not in primary:
                        violations.append(
                            {
                                "rule": "Do not introduce a competing ORM",
                                "evidence": f"Existing stack: {', '.join(orms)}",
                                "why": "Multiple ORMs fragment data-access conventions.",
                                "recommended_alternative": f"Implement the change with {orms[0]}.",
                            }
                        )

    if constitution.get("authentication", {}).get("files") and any(
        t in proposal_l for t in ("new auth system", "roll our own jwt from scratch", "bypass middleware")
    ):
        violations.append(
            {
                "rule": "Extend existing authentication",
                "evidence": ", ".join(constitution["authentication"]["files"][:3]),
                "why": "A parallel auth path usually breaks session and authorization consistency.",
                "recommended_alternative": "Hook into existing auth/session middleware files.",
            }
        )

    # Duplicate feature smell
    if "redux" in proposal_l and any("react-query" in str(d).lower() or "tanstack" in str(d).lower() for d in constitution.get("dependency_conventions", {}).get("notable_dependencies") or []):
        violations.append(
            {
                "rule": "Avoid duplicating server-state libraries",
                "evidence": "React Query / TanStack already present",
                "why": "Redux for server state duplicates an existing pattern.",
                "recommended_alternative": "Use the existing server-state library.",
            }
        )

    status = "fail" if violations else "pass"
    return {
        "status": status,
        "violations": violations,
        "constitution_summary": {
            "preferred_flow": constitution.get("architecture", {}).get("preferred_flow"),
            "orm": orms,
            "forbidden_count": len(constitution.get("forbidden_patterns") or []),
        },
    }
