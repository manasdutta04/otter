"""Otter agent core — types for the AI Software Engineer orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class EngineerState(str, Enum):
    IDLE = "idle"
    UNDERSTAND = "understand"
    INVESTIGATE = "investigate"
    PLAN = "plan"
    DECOMPOSE = "decompose"
    AWAIT_APPROVAL = "await_approval"
    IMPLEMENT = "implement"
    VALIDATE = "validate"
    DEBUG = "debug"
    REVIEW = "review"
    FINAL_APPROVAL = "final_approval"
    APPLY = "apply"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DONE = "done"


class WorkerRole(str, Enum):
    EXPLORER = "explorer"
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ToolKind(str, Enum):
    READ = "read"
    WRITE = "write"
    EXEC = "exec"


# Map legacy CodeChangeTask statuses ↔ engineer states (API compatibility).
CODE_TASK_TO_ENGINEER: dict[str, EngineerState] = {
    "draft": EngineerState.IDLE,
    "ready_for_approval": EngineerState.AWAIT_APPROVAL,
    "patch_ready": EngineerState.FINAL_APPROVAL,
    "approved": EngineerState.APPLY,
    "rejected": EngineerState.CANCELLED,
    "applied": EngineerState.DONE,
}

ENGINEER_TO_CODE_TASK: dict[EngineerState, str] = {
    EngineerState.IDLE: "draft",
    EngineerState.UNDERSTAND: "ready_for_approval",
    EngineerState.INVESTIGATE: "ready_for_approval",
    EngineerState.PLAN: "ready_for_approval",
    EngineerState.DECOMPOSE: "ready_for_approval",
    EngineerState.AWAIT_APPROVAL: "ready_for_approval",
    EngineerState.IMPLEMENT: "ready_for_approval",
    EngineerState.VALIDATE: "patch_ready",
    EngineerState.DEBUG: "ready_for_approval",
    EngineerState.REVIEW: "patch_ready",
    EngineerState.FINAL_APPROVAL: "patch_ready",
    EngineerState.APPLY: "approved",
    EngineerState.DONE: "applied",
    EngineerState.FAILED: "rejected",
    EngineerState.CANCELLED: "rejected",
}


@dataclass
class ToolSpec:
    name: str
    kind: ToolKind
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelBudget:
    """Adaptive limits for the selected LLM (small-model friendly defaults)."""

    model: str
    max_context_files: int = 4
    max_chars_per_file: int = 1800
    max_tool_calls: int = 8
    max_worker_iterations: int = 4
    max_subtasks: int = 8
    prefer_targeted_edits: bool = True
    tier: Literal["small", "medium", "large"] = "medium"


@dataclass
class ContextFile:
    path: str
    content: str
    score: float = 0.0
    symbols: list[str] = field(default_factory=list)


@dataclass
class ContextBundle:
    task: str
    files: list[ContextFile] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    git_status: str = ""
    plan_summary: str = ""
    constraints: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    char_count: int = 0

    def bounded_files(self, max_files: int, max_chars: int) -> list[ContextFile]:
        out: list[ContextFile] = []
        for item in self.files[:max_files]:
            content = item.content if item.path.split("/")[-1].lower() in {
                "package.json",
                "pyproject.toml",
                "requirements.txt",
            } else item.content[:max_chars]
            out.append(ContextFile(path=item.path, content=content, score=item.score, symbols=item.symbols))
        return out


@dataclass
class TaskNode:
    id: str
    title: str
    description: str = ""
    role: WorkerRole = WorkerRole.IMPLEMENTER
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = field(default_factory=list)
    allowed_files: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    confidence: Confidence = Confidence.MEDIUM
    evidence: list[str] = field(default_factory=list)
    retries: int = 0


@dataclass
class TaskGraph:
    nodes: dict[str, TaskNode] = field(default_factory=dict)

    def add(self, node: TaskNode) -> None:
        self.nodes[node.id] = node

    def ready_nodes(self) -> list[TaskNode]:
        ready: list[TaskNode] = []
        for node in self.nodes.values():
            if node.status not in {TaskStatus.PENDING, TaskStatus.BLOCKED, TaskStatus.READY}:
                continue
            deps_ok = all(
                self.nodes[d].status == TaskStatus.DONE
                for d in node.depends_on
                if d in self.nodes
            )
            if deps_ok:
                node.status = TaskStatus.READY
                ready.append(node)
            else:
                node.status = TaskStatus.BLOCKED
        return ready

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "description": n.description,
                    "role": n.role.value,
                    "status": n.status.value,
                    "depends_on": n.depends_on,
                    "allowed_files": n.allowed_files,
                    "allowed_tools": n.allowed_tools,
                    "confidence": n.confidence.value,
                    "evidence": n.evidence,
                    "result": n.result,
                    "retries": n.retries,
                }
                for n in self.nodes.values()
            ]
        }


@dataclass
class WorkerResult:
    role: WorkerRole
    ok: bool
    summary: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    patch_ops: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentRun:
    id: str
    repository_id: str
    request: str
    state: EngineerState = EngineerState.IDLE
    model: str = "qwen2.5-coder:7b"
    budget: ModelBudget | None = None
    context: ContextBundle | None = None
    graph: TaskGraph | None = None
    worker_results: list[WorkerResult] = field(default_factory=list)
    patch_files: list[dict[str, str]] = field(default_factory=list)
    plan_id: str | None = None
    code_task_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "request": self.request,
            "state": self.state.value,
            "model": self.model,
            "plan_id": self.plan_id,
            "code_task_id": self.code_task_id,
            "error": self.error,
            "graph": self.graph.to_dict() if self.graph else None,
            "patch_files": self.patch_files,
            "worker_results": [
                {
                    "role": w.role.value,
                    "ok": w.ok,
                    "summary": w.summary,
                    "confidence": w.confidence.value,
                    "evidence": w.evidence,
                    "data": w.data,
                }
                for w in self.worker_results
            ],
        }


__all__ = [
    "AgentRun",
    "CODE_TASK_TO_ENGINEER",
    "Confidence",
    "ContextBundle",
    "ContextFile",
    "ENGINEER_TO_CODE_TASK",
    "EngineerState",
    "ModelBudget",
    "TaskGraph",
    "TaskNode",
    "TaskStatus",
    "ToolKind",
    "ToolSpec",
    "WorkerResult",
    "WorkerRole",
]
