"""Resolve repository filesystem root with traversal protection."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import OtterMcpConfig, load_config
from .errors import OtterMcpError


@dataclass
class RepoContext:
    root: Path
    repository_id: str | None
    source: str


def _safe_join(base: Path, *parts: str) -> Path:
    candidate = (base.joinpath(*parts)).resolve()
    base_resolved = base.resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise OtterMcpError(
            "path_traversal",
            "Resolved path escapes the repository data directory.",
            "Use a valid repository_id without .. segments.",
        )
    return candidate


def resolve_repo(
    repository_id: str | None = None,
    repo_root: str | None = None,
    *,
    cfg: OtterMcpConfig | None = None,
) -> RepoContext:
    cfg = cfg or load_config()
    if repo_root:
        root = Path(repo_root).expanduser().resolve()
        if not root.is_dir():
            raise OtterMcpError(
                "repo_root_missing",
                f"OTTER_REPO_ROOT / repo_root is not a directory: {root}",
                "Point repo_root at an existing checkout.",
            )
        return RepoContext(root=root, repository_id=repository_id or cfg.repository_id, source="explicit_root")

    if cfg.repo_root and cfg.repo_root.is_dir():
        return RepoContext(root=cfg.repo_root, repository_id=repository_id or cfg.repository_id, source="env_root")

    rid = repository_id or cfg.repository_id
    if rid:
        if ".." in rid.replace("\\", "/").split("/"):
            raise OtterMcpError("invalid_repository_id", "repository_id must not contain '..'.")
        root = _safe_join(cfg.repository_data_dir, rid)
        if root.is_dir():
            return RepoContext(root=root, repository_id=rid, source="data_dir")
        # Also try CLI-style clones under ~/.otter/repos
        alt = Path.home() / ".otter" / "repos"
        if alt.is_dir():
            for child in alt.iterdir():
                if child.is_dir() and rid in child.name:
                    return RepoContext(root=child.resolve(), repository_id=rid, source="cli_repos")
        raise OtterMcpError(
            "repository_not_imported",
            f"Repository `{rid}` was not found under {cfg.repository_data_dir}.",
            "Import the repository in Otter Web/API, or set OTTER_REPO_ROOT to a local checkout.",
        )

    raise OtterMcpError(
        "repository_unbound",
        "No repository bound for this MCP session.",
        "Pass repository_id, or set OTTER_REPO_ROOT / OTTER_REPOSITORY_ID.",
    )


def safe_rel_path(root: Path, relative: str) -> Path:
    rel = relative.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise OtterMcpError("path_traversal", "Relative path must not contain '..'.")
    path = (root / rel).resolve()
    if path != root.resolve() and root.resolve() not in path.parents:
        raise OtterMcpError("path_traversal", "Path escapes repository root.")
    return path
