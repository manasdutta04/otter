from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .models import AuthSession, Repository, RepositoryImportJob

class RepositoryStore:
    def __init__(self) -> None:
        self.root = Path(get_settings().repository_data_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    async def list(self, db: AsyncSession, user_id: str) -> list[Repository]:
        result = await db.scalars(select(Repository).where(Repository.user_id == user_id).order_by(Repository.created_at.desc()))
        return list(result)

    async def create(self, db: AsyncSession, user_id: str, url: str) -> tuple[Repository, RepositoryImportJob]:
        repository_id = uuid4().hex[:12]
        name = url.rstrip("/").split("/")[-1].removesuffix(".git") or "repository"
        record = Repository(id=repository_id, user_id=user_id, url=url, name=name, status="queued")
        job = RepositoryImportJob(id=uuid4().hex[:12], repository_id=repository_id, user_id=user_id, status="queued")
        db.add(record)
        db.add(job)
        await db.commit()
        await db.refresh(record)
        await db.refresh(job)
        return record, job

    async def get(self, db: AsyncSession, user_id: str, repository_id: str) -> Repository | None:
        return await db.scalar(select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id))

    async def get_job(self, db: AsyncSession, user_id: str, repository_id: str) -> RepositoryImportJob | None:
        return await db.scalar(select(RepositoryImportJob).where(RepositoryImportJob.repository_id == repository_id, RepositoryImportJob.user_id == user_id).order_by(RepositoryImportJob.created_at.desc()))

    async def get_session_token(self, db: AsyncSession, user_id: str) -> str | None:
        session = await db.scalar(select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.expires_at > datetime.now(timezone.utc)).order_by(AuthSession.expires_at.desc()))
        return session.github_token if session else None
