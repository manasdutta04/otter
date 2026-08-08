"""Tool registry — controlled repository tools with role-based permissions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from packages.agent.types import ToolKind, ToolSpec, WorkerRole

SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".next"}


def _safe(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    root_r = root.resolve()
    if root_r not in target.parents and target != root_r:
        raise PermissionError(f"Path escapes workspace: {rel}")
    return target


READ_TOOLS = [
    ToolSpec("repo_tree", ToolKind.READ, "List directory tree", {"path": "string", "depth": "number"}),
    ToolSpec("search_code", ToolKind.READ, "Search file contents", {"query": "string"}),
    ToolSpec("find_symbol", ToolKind.READ, "Find symbol-like definitions", {"name": "string"}),
    ToolSpec("read_file", ToolKind.READ, "Read a file", {"path": "string", "start": "number", "end": "number"}),
    ToolSpec("git_status", ToolKind.READ, "Git status summary", {}),
    ToolSpec("git_diff", ToolKind.READ, "Git diff", {}),
]

WRITE_TOOLS = [
    ToolSpec("apply_edit", ToolKind.WRITE, "Exact string replace in a file", {"path": "string", "old_string": "string", "new_string": "string"}),
    ToolSpec("create_file", ToolKind.WRITE, "Create a new file", {"path": "string", "content": "string"}),
    ToolSpec("apply_patch_files", ToolKind.WRITE, "Write full file contents (fallback)", {"path": "string", "content": "string"}),
]

EXEC_TOOLS = [
    ToolSpec("run_tests", ToolKind.EXEC, "Run repository tests (restricted)", {}),
]

ROLE_ALLOW: dict[WorkerRole, set[str]] = {
    WorkerRole.EXPLORER: {t.name for t in READ_TOOLS},
    WorkerRole.PLANNER: {t.name for t in READ_TOOLS},
    WorkerRole.REVIEWER: {t.name for t in READ_TOOLS},
    WorkerRole.DEBUGGER: {t.name for t in READ_TOOLS} | {"run_tests"},
    WorkerRole.TESTER: {t.name for t in READ_TOOLS} | {"run_tests"},
    WorkerRole.IMPLEMENTER: {t.name for t in READ_TOOLS} | {t.name for t in WRITE_TOOLS} | {"run_tests"},
}


class ToolPermissionError(PermissionError):
    pass


class ToolRegistry:
    def __init__(self, repo_root: Path | str, *, allowed_files: list[str] | None = None):
        self.root = Path(repo_root)
        self.allowed_files = set(allowed_files or [])
        self.specs = {t.name: t for t in [*READ_TOOLS, *WRITE_TOOLS, *EXEC_TOOLS]}

    def allowed_for(self, role: WorkerRole) -> list[ToolSpec]:
        names = ROLE_ALLOW.get(role, set())
        return [self.specs[n] for n in names if n in self.specs]

    def assert_allowed(self, role: WorkerRole, tool_name: str) -> None:
        if tool_name not in ROLE_ALLOW.get(role, set()):
            raise ToolPermissionError(f"Role {role.value} cannot use tool {tool_name}")

    def _assert_file_scope(self, rel: str, role: WorkerRole) -> None:
        if role != WorkerRole.IMPLEMENTER:
            return
        if not self.allowed_files:
            return
        norm = rel.replace("\\", "/")
        if norm not in self.allowed_files and not any(norm.startswith(a.rstrip("/") + "/") for a in self.allowed_files):
            # Also allow manifests
            if Path(norm).name.lower() not in {"package.json", "pyproject.toml", "requirements.txt"}:
                raise ToolPermissionError(f"Implementer cannot modify {rel}; not in allowed scope")

    def run(self, role: WorkerRole, name: str, args: dict[str, Any] | None = None) -> str:
        self.assert_allowed(role, name)
        args = args or {}
        handler: Callable[..., str] = getattr(self, f"_tool_{name}")
        return handler(role=role, **args)

    def _tool_repo_tree(self, role: WorkerRole, path: str = ".", depth: int = 2, **_: Any) -> str:
        base = _safe(self.root, path)
        lines: list[str] = []

        def walk(current: Path, d: int, prefix: str) -> None:
            if d < 0:
                return
            try:
                entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except OSError:
                return
            for entry in entries[:80]:
                if entry.name in SKIP_DIRS:
                    continue
                lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
                if entry.is_dir() and d > 0:
                    walk(entry, d - 1, prefix + "  ")

        walk(base, int(depth), "")
        return "\n".join(lines[:200])

    def _tool_search_code(self, role: WorkerRole, query: str, **_: Any) -> str:
        hits: list[str] = []
        pattern = re.compile(re.escape(query), re.I)
        for path in self.root.rglob("*"):
            if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    rel = str(path.relative_to(self.root)).replace("\\", "/")
                    hits.append(f"{rel}:{i}:{line.strip()[:160]}")
                    if len(hits) >= 40:
                        return "\n".join(hits)
        return "\n".join(hits) or "No matches"

    def _tool_find_symbol(self, role: WorkerRole, name: str, **_: Any) -> str:
        # Deterministic-ish: look for def/class/function/const patterns
        patterns = [
            re.compile(rf"^\s*(def|class|function|const|let|var|export\s+(async\s+)?function)\s+{re.escape(name)}\b"),
            re.compile(rf"^\s*{re.escape(name)}\s*="),
        ]
        hits: list[str] = []
        for path in self.root.rglob("*"):
            if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                if any(p.search(line) for p in patterns):
                    rel = str(path.relative_to(self.root)).replace("\\", "/")
                    hits.append(f"{rel}:{i}:{line.strip()[:160]}")
                    if len(hits) >= 30:
                        return "\n".join(hits)
        return "\n".join(hits) or "No symbol matches"

    def _tool_read_file(self, role: WorkerRole, path: str, start: int = 1, end: int = 0, **_: Any) -> str:
        target = _safe(self.root, path)
        text = target.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        s = max(1, int(start)) - 1
        e = int(end) if int(end) > 0 else len(lines)
        return "\n".join(lines[s:e][:400])

    def _tool_git_status(self, role: WorkerRole, **_: Any) -> str:
        try:
            from git import Repo

            repo = Repo(self.root)
            return repo.git.status("--short")
        except Exception as exc:  # noqa: BLE001
            return f"git status unavailable: {exc}"

    def _tool_git_diff(self, role: WorkerRole, **_: Any) -> str:
        try:
            from git import Repo

            repo = Repo(self.root)
            return (repo.git.diff() or "")[:8000]
        except Exception as exc:  # noqa: BLE001
            return f"git diff unavailable: {exc}"

    def _tool_apply_edit(
        self,
        role: WorkerRole,
        path: str,
        old_string: str,
        new_string: str,
        **_: Any,
    ) -> str:
        self._assert_file_scope(path, role)
        target = _safe(self.root, path)
        text = target.read_text(encoding="utf-8")
        if old_string not in text:
            raise ValueError("old_string not found in file")
        if text.count(old_string) != 1:
            raise ValueError("old_string is not unique in file")
        target.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
        return f"edited {path}"

    def _tool_create_file(self, role: WorkerRole, path: str, content: str, **_: Any) -> str:
        self._assert_file_scope(path, role)
        target = _safe(self.root, path)
        if target.exists():
            raise ValueError("file already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"created {path}"

    def _tool_apply_patch_files(self, role: WorkerRole, path: str, content: str, **_: Any) -> str:
        self._assert_file_scope(path, role)
        target = _safe(self.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {path}"

    def _tool_run_tests(self, role: WorkerRole, **_: Any) -> str:
        # Placeholder — API uses run_repository_tests; registry returns guidance.
        return "Use API run_repository_tests for full test execution"


__all__ = [
    "ROLE_ALLOW",
    "ToolPermissionError",
    "ToolRegistry",
]
