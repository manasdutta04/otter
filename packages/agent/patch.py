"""Targeted patch operations — prefer edit ops over full-file rewrites."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_patch_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """
    Accept either:
      - files: [{path, content}]  (legacy full-file)
      - edits: [{path, old_string, new_string}]  (targeted)
    Returns unified {summary, files, edits}.
    """
    summary = str(proposal.get("summary") or "")
    files = list(proposal.get("files") or [])
    edits = list(proposal.get("edits") or [])
    # Some models nest under "patch"
    if not files and not edits and isinstance(proposal.get("patch"), dict):
        inner = proposal["patch"]
        files = list(inner.get("files") or [])
        edits = list(inner.get("edits") or [])
        summary = summary or str(inner.get("summary") or "")
    return {"summary": summary, "files": files, "edits": edits}


def apply_edits_to_originals(
    edits: list[dict[str, Any]],
    originals: dict[str, str],
) -> list[dict[str, str]]:
    """Materialize full-file snapshots from targeted edits for existing apply pipeline."""
    working = dict(originals)
    changed: set[str] = set()
    for edit in edits:
        path = str(edit.get("path") or "").replace("\\", "/")
        old = str(edit.get("old_string") or "")
        new = str(edit.get("new_string") or "")
        if not path or old is None:
            continue
        current = working.get(path)
        if current is None:
            # New file via edit with empty old_string
            if old == "":
                working[path] = new
                changed.add(path)
            continue
        if old not in current:
            raise ValueError(f"Edit target not found in {path}")
        if current.count(old) != 1:
            raise ValueError(f"Edit target not unique in {path}")
        working[path] = current.replace(old, new, 1)
        changed.add(path)
    return [{"path": p, "content": working[p]} for p in changed]


def prefer_targeted_files(
    proposal: dict[str, Any],
    originals: dict[str, str],
) -> list[dict[str, str]]:
    """
    Prefer edits when present; otherwise use full files.
    Returns list[{path, content}] suitable for CodeChangeTask.patch_json.
    """
    norm = normalize_patch_proposal(proposal)
    if norm["edits"]:
        return apply_edits_to_originals(norm["edits"], originals)
    safe: list[dict[str, str]] = []
    for item in norm["files"]:
        path = str(item.get("path") or "").replace("\\", "/")
        if not path or Path(path).is_absolute() or ".." in Path(path).parts:
            continue
        safe.append({"path": path, "content": str(item.get("content") or "")})
    return safe


def edit_prompt_addon() -> str:
    return (
        "Prefer targeted edits when possible. You may return JSON with either:\n"
        '  "edits": [{"path": "...", "old_string": "...", "new_string": "..."}]\n'
        "or legacy full files:\n"
        '  "files": [{"path": "...", "content": "..."}]\n'
        "Use the smallest change that satisfies the request."
    )


__all__ = [
    "apply_edits_to_originals",
    "edit_prompt_addon",
    "normalize_patch_proposal",
    "prefer_targeted_files",
]
