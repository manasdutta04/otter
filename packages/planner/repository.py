from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RepositoryPlan
from packages.planner import build_plan as _build_plan


def build_plan(root: Path, request: str, intelligence: dict[str, object] | None) -> dict[str, object]:
    return _build_plan(root, request, intelligence)


async def save_plan(db: AsyncSession, repository_id: str, user_id: str, request: str, plan: dict[str, object]) -> RepositoryPlan:
    record = RepositoryPlan(
        id=uuid4().hex[:12],
        repository_id=repository_id,
        user_id=user_id,
        request=request,
        title=str(plan["title"]),
        complexity=str(plan["complexity"]),
        summary=str(plan["summary"]),
        steps=json.dumps(plan["steps"]),
        affected_files=json.dumps(plan["affected_files"]),
        dependencies=json.dumps(plan["dependencies"]),
        risks=json.dumps(plan["risks"]),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
