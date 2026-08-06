import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from .models import RepositoryHealth

async def analyze_health(db: AsyncSession, repository_id: str, root: Path, file_count: int) -> RepositoryHealth:
    files = [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    names = {path.name.lower() for path in files}
    findings: list[str] = []
    documentation = 100 if any(name.startswith("readme") for name in names) else 45
    security = 100
    if any(name in {".env", ".env.local", "id_rsa"} for name in names): findings.append("Sensitive-looking files are present in the repository tree."); security -= 35
    if not any("test" in str(path).lower() for path in files): findings.append("No obvious test directory or test file was detected."); maintainability = 55
    else: maintainability = 80
    if not any(name in {"requirements.txt", "pyproject.toml", "package.json", "go.mod", "cargo.toml"} for name in names): findings.append("No conventional dependency manifest was detected."); dependency = 50
    else: dependency = 80
    complexity = max(35, 100 - min(65, file_count // 10))
    architecture = 75 if any(name in {"dockerfile", "docker-compose.yml", "compose.yml"} for name in names) else 60
    performance = 70 if file_count < 500 else 55
    debt = max(30, 100 - len(findings) * 20)
    record = RepositoryHealth(repository_id=repository_id, architecture_score=architecture, security_score=security, maintainability_score=maintainability, performance_score=performance, debt_score=debt, documentation_score=documentation, dependency_score=dependency, complexity_score=complexity, findings=json.dumps(findings), analyzed_at=datetime.now(timezone.utc))
    merged_record = await db.merge(record)
    await db.commit()
    await db.refresh(merged_record)
    return merged_record
