import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from git import Repo
from .config import get_settings

@dataclass
class RepositoryRecord:
    id: str
    url: str
    name: str
    status: str
    created_at: str
    branch: str | None = None
    file_count: int = 0
    error: str | None = None

class RepositoryStore:
    def __init__(self) -> None:
        self.root = Path(get_settings().repository_data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, RepositoryRecord] = {}
        self._lock = asyncio.Lock()

    async def list(self) -> list[RepositoryRecord]:
        async with self._lock:
            return list(self._records.values())

    async def create(self, url: str) -> RepositoryRecord:
        repository_id = uuid4().hex[:12]
        name = url.rstrip("/").split("/")[-1].removesuffix(".git") or "repository"
        record = RepositoryRecord(repository_id, url, name, "queued", datetime.now(timezone.utc).isoformat())
        async with self._lock:
            self._records[repository_id] = record
        asyncio.create_task(self._clone(record))
        return record

    async def get(self, repository_id: str) -> RepositoryRecord | None:
        async with self._lock:
            return self._records.get(repository_id)

    async def _clone(self, record: RepositoryRecord) -> None:
        record.status = "cloning"
        destination = self.root / record.id
        try:
            await asyncio.to_thread(Repo.clone_from, record.url, destination, depth=1)
            files = [path for path in destination.rglob("*") if path.is_file() and ".git" not in path.parts]
            repository = await asyncio.to_thread(Repo, destination)
            record.branch = repository.active_branch.name
            record.file_count = len(files)
            record.status = "ready"
        except Exception as exc:  # noqa: BLE001
            record.status = "failed"
            record.error = str(exc)
