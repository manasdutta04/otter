import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryPerformance

PATTERNS = [(re.compile(r"for\s+.+\s+in\s+.+:\s*\n\s*.+\.execute\(", re.M), "Query execution inside a loop", "medium"), (re.compile(r"SELECT\s+\*", re.I), "SELECT * may transfer unnecessary columns", "low"), (re.compile(r"\.rglob\(|os\.walk\(", re.I), "Recursive filesystem traversal", "low")]
async def analyze_performance(db: AsyncSession, repository_id: str, root: Path) -> RepositoryPerformance:
    hotspots = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".java", ".go"}: continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, title, severity in PATTERNS:
            match = pattern.search(content)
            if match: hotspots.append({"file": str(path.relative_to(root)).replace("\\", "/"), "line": content[:match.start()].count("\n") + 1, "title": title, "severity": severity})
    score = max(30, 100 - len(hotspots) * 12)
    record = RepositoryPerformance(repository_id=repository_id, score=score, hotspots=json.dumps(hotspots[:100]), created_at=datetime.now(timezone.utc)); await db.merge(record); await db.commit(); await db.refresh(record); return record
