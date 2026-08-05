from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str

class RepositoryCreate(BaseModel):
    url: str = Field(min_length=1)

class RepositorySummary(BaseModel):
    id: str
    url: str
    name: str
    status: Literal["queued", "cloning", "ready", "failed"]
    created_at: datetime
    branch: str | None = None
    file_count: int = 0
    error: str | None = None

class RepositoryListResponse(BaseModel):
    repositories: list[RepositorySummary]

class ImportStatus(BaseModel):
    job_id: str
    repository_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    attempt_count: int
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
