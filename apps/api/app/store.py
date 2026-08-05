import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from git import Repo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .models import Repository

class RepositoryStore:
    def __init__(self) -> None:
        self.root = Path(get_settings().repository_data_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    async def list(self, db: AsyncSession, user_id: str) -> list[Repository]:
        result = await db.scalars(select(Repository).where(Repository.user_id == user_id).order_by(Repository.created_at.desc()))
        return list(result)

    async def create(self, db: AsyncSession, user_id: str, url: str, access_token: str) -> Repository:
        repository_id = uuid4().hex[:12]
        name = url.rstrip("/").split("/")[-1].removesuffix(".git") or "repository"
        record = Repository(id=repository_id, user_id=user_id, url=url, name=name, status="queued")
        db.add(record)
        await db.commit()
        await db.refresh(record)
        asyncio.create_task(self._clone(record.id, url, access_token))
        return record

    async def get(self, db: AsyncSession, user_id: str, repository_id: str) -> Repository | None:
        return await db.scalar(select(Repository).where(Repository.id == repository_id, Repository.user_id == user_id))

    async def _clone(self, repository_id: str, url: str, access_token: str) -> None:
        destination = self.root / repository_id
        async with __import__("app.database", fromlist=["SessionLocal"]).SessionLocal() as db:
            record = await db.get(Repository, repository_id)
            if not record:
                return
            record.status = "cloning"
            await db.commit()
        try:
            clone_url = url.replace("https://github.com/", f"https://x-access-token:{access_token}@github.com/", 1)
            await asyncio.to_thread(Repo.clone_from, clone_url, destination, depth=1)
            files = [path for path in destination.rglob("*") if path.is_file() and ".git" not in path.parts]
            repository = await asyncio.to_thread(Repo, destination)
            async with __import__("app.database", fromlist=["SessionLocal"]).SessionLocal() as db:
                record = await db.get(Repository, repository_id)
                record.branch = repository.active_branch.name
                record.file_count = len(files)
                record.status = "ready"
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            async with __import__("app.database", fromlist=["SessionLocal"]).SessionLocal() as db:
                record = await db.get(Repository, repository_id)
                if record:
                    record.status = "failed"
                    record.error = str(exc)
                    await db.commit()
