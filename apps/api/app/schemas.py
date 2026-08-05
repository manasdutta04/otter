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

class IntelligenceResponse(BaseModel):
    repository_id: str
    summary: str
    tech_stack: list[str]
    folders: list[str]
    entry_points: list[str]
    architecture_signals: list[str]
    analyzed_at: datetime

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

class PlanRequest(BaseModel):
    request: str = Field(min_length=8, max_length=2000)

class PlanResponse(BaseModel):
    id: str
    repository_id: str
    request: str
    title: str
    complexity: Literal["low", "medium", "high"]
    summary: str
    steps: list[str]
    affected_files: list[str]
    dependencies: list[str]
    risks: list[str]
    created_at: datetime

class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    path: str

class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str

class ArchitectureGraphResponse(BaseModel):
    repository_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    generated_at: datetime

class MemoryCreate(BaseModel):
    kind: Literal["decision", "convention", "note"] = "note"
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2, max_length=5000)

class MemoryResponse(BaseModel):
    id: str
    repository_id: str
    kind: str
    title: str
    content: str
    created_at: datetime

class DocumentResponse(BaseModel):
    id: str
    repository_id: str
    kind: str
    title: str
    content: str
    created_at: datetime

class CodeTaskCreate(BaseModel):
    request: str = Field(min_length=8, max_length=2000)
    plan_id: str | None = None

class CodeTaskDecision(BaseModel):
    note: str | None = Field(default=None, max_length=2000)

class CodeTaskResponse(BaseModel):
    id: str
    repository_id: str
    plan_id: str | None
    request: str
    status: Literal["draft", "ready_for_approval", "approved", "rejected"]
    proposed_summary: str
    approval_note: str | None
    created_at: datetime
    approved_at: datetime | None

class MemoryCreate(BaseModel):
    kind: Literal["decision", "convention", "note"] = "note"
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2, max_length=5000)

class MemoryResponse(BaseModel):
    id: str
    repository_id: str
    kind: str
    title: str
    content: str
    created_at: datetime

class DocumentResponse(BaseModel):
    id: str
    repository_id: str
    kind: str
    title: str
    content: str
    created_at: datetime

class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    path: str

class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str

class ArchitectureGraphResponse(BaseModel):
    repository_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    generated_at: datetime
