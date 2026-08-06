from datetime import datetime
from typing import Literal
import json
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
    status: Literal["draft", "ready_for_approval", "patch_ready", "approved", "rejected", "applied"]
    proposed_summary: str
    changed_files: list[str] = []
    approval_note: str | None
    created_at: datetime
    approved_at: datetime | None
    applied_at: datetime | None

    @classmethod
    def from_task(cls, task: object) -> "CodeTaskResponse":
        changed = getattr(task, "changed_files", "[]")
        if isinstance(changed, str):
            try:
                changed = json.loads(changed)
            except json.JSONDecodeError:
                changed = []
        return cls(
            id=task.id,
            repository_id=task.repository_id,
            plan_id=task.plan_id,
            request=task.request,
            status=task.status,
            proposed_summary=task.proposed_summary,
            changed_files=list(changed or []),
            approval_note=task.approval_note,
            created_at=task.created_at,
            approved_at=task.approved_at,
            applied_at=task.applied_at,
        )

class PatchFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=500000)

class PatchProposal(BaseModel):
    summary: str = Field(min_length=8, max_length=2000)
    files: list[PatchFile] = Field(min_length=1, max_length=50)

class TestResponse(BaseModel):
    passed: bool
    output: str

class PullRequestRequest(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    base: str = "main"

class PullRequestResponse(BaseModel):
    url: str
    number: int
    branch: str

class HealthResponseReport(BaseModel):
    repository_id: str
    architecture_score: int
    security_score: int
    maintainability_score: int
    performance_score: int
    debt_score: int
    documentation_score: int
    dependency_score: int
    complexity_score: int
    findings: list[str]
    analyzed_at: datetime

class ReviewFinding(BaseModel):
    category: str
    severity: Literal["low", "medium", "high"]
    title: str
    file: str
    line: int

class ReviewResponse(BaseModel):
    id: str
    repository_id: str
    findings: list[ReviewFinding]
    created_at: datetime

class ArchitectureAnalysisResponse(BaseModel):
    repository_id: str
    score: int
    findings: list[dict[str, object]]
    created_at: datetime

class PerformanceResponse(BaseModel):
    repository_id: str
    score: int
    hotspots: list[dict[str, object]]
    created_at: datetime

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
