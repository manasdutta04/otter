import json, re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryReview

PATTERNS = [("security", "high", re.compile(r"(api[_-]?key|secret|password|token)\s*[=:]\s*[\"'][^\"']+", re.I), "Possible hardcoded credential"), ("reliability", "medium", re.compile(r"except\s*:\s*$", re.M), "Bare exception handler can hide failures"), ("maintainability", "low", re.compile(r"TODO|FIXME", re.I), "Unresolved maintenance marker")]
def review_repository(root: Path) -> list[dict[str, object]]:
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".java", ".go"}: continue
        content = path.read_text(encoding="utf-8", errors="ignore"); relative = str(path.relative_to(root)).replace("\\", "/")
        for category, severity, pattern, title in PATTERNS:
            match = pattern.search(content)
            if match: findings.append({"category": category, "severity": severity, "title": title, "file": relative, "line": content[:match.start()].count("\n") + 1})
    return findings[:100]
async def save_review(db: AsyncSession, repository_id: str, user_id: str, findings: list[dict[str, object]]) -> RepositoryReview:
    record = RepositoryReview(id=uuid4().hex[:12], repository_id=repository_id, user_id=user_id, findings=json.dumps(findings), created_at=datetime.now(timezone.utc)); db.add(record); await db.commit(); await db.refresh(record); return record
