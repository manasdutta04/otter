import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryArchitectureAnalysis

async def analyze_architecture(db: AsyncSession, repository_id: str, root: Path) -> RepositoryArchitectureAnalysis:
    files = [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    findings = []
    deep = [path for path in files if len(path.relative_to(root).parts) > 6]
    if deep: findings.append({"severity": "medium", "title": "Deep folder nesting", "detail": f"{len(deep)} files are nested more than six levels deep."})
    if not any(path.name.lower().startswith("readme") for path in files): findings.append({"severity": "low", "title": "Missing repository overview", "detail": "No README file was detected."})
    if not any("config" in path.name.lower() for path in files): findings.append({"severity": "low", "title": "Configuration boundary unclear", "detail": "No conventional configuration file was detected."})
    score = max(30, 100 - len(findings) * 15)
    record = RepositoryArchitectureAnalysis(repository_id=repository_id, score=score, findings=json.dumps(findings), created_at=datetime.now(timezone.utc))
    merged_record = await db.merge(record)
    await db.commit()
    await db.refresh(merged_record)
    return merged_record
