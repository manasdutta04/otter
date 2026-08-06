"""Shared types for repository intelligence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FolderInfo:
    path: str
    role: str
    file_count: int


@dataclass
class ApiRoute:
    method: str
    path: str
    file: str
    line: int | None = None


@dataclass
class DatabaseSignal:
    orm: str
    evidence: str
    files: list[str] = field(default_factory=list)


@dataclass
class AuthSignal:
    mechanism: str
    files: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class DependencyInfo:
    name: str
    version: str


@dataclass
class RepositoryAnalysis:
    summary_facts: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    folders: list[FolderInfo] = field(default_factory=list)
    api_routes: list[ApiRoute] = field(default_factory=list)
    databases: list[DatabaseSignal] = field(default_factory=list)
    auth: list[AuthSignal] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    ci: list[str] = field(default_factory=list)
    docker: list[str] = field(default_factory=list)
    testing: list[str] = field(default_factory=list)
    dependency_manifest: list[DependencyInfo] = field(default_factory=list)
    architecture_signals: list[str] = field(default_factory=list)
    # Human summary filled later by explain layer or facts join
    summary: str = ""
    folder_explanations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".turbo",
    "coverage",
    ".cache",
}
