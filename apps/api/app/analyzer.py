"""Legacy analyzer entry — delegates to Phase 1 intelligence package."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .intelligence import analyze_repository, analysis_to_legacy_dict
from .models import RepositoryIntelligence


def inspect_repository(root: Path) -> dict[str, object]:
    analysis = analyze_repository(Path(root))
    return analysis_to_legacy_dict(analysis)


async def save_intelligence(db: AsyncSession, repository_id: str, data: dict[str, object]) -> None:
    analysis_blob = data.get("analysis")
    if analysis_blob is None:
        analysis_blob = {}
    folders = data.get("folders_rich") or data.get("folders") or []
    record = RepositoryIntelligence(
        repository_id=repository_id,
        summary=str(data.get("summary") or ""),
        tech_stack=json.dumps(data.get("tech_stack") or []),
        folders=json.dumps(folders),
        entry_points=json.dumps(data.get("entry_points") or []),
        architecture_signals=json.dumps(data.get("architecture_signals") or []),
        analysis_json=json.dumps(analysis_blob),
        analyzed_at=datetime.now(timezone.utc),
    )
    await db.merge(record)
    await db.commit()
