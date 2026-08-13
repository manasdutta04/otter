"""Targeted patch operations — prefer edit ops over full-file rewrites."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

_NAME_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:def|class|function|const|let|var)\s+(\w+)",
    re.MULTILINE,
)


class QualityGateError(ValueError):
    """Structured quality-gate rejection. Safe to raise through generate_patch."""

    def __init__(self, category: str, reason: str, file: str | None = None, **details: Any):
        self.category = category
        self.reason = reason
        self.file = file
        self.details = details
        lines = ["QUALITY_GATE:", f"    category: {category}"]
        if file:
            lines.append(f"    file: {file}")
        lines.append(f"    reason: {reason}")
        super().__init__("\n".join(lines))

    def as_dict(self) -> dict[str, Any]:
        payload = {"category": self.category, "reason": self.reason, "file": self.file}
        payload.update(self.details)
        return payload


def normalize_patch_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """
    Accept either:
      - files: [{path, content}]  (legacy full-file)
      - edits: [{path, old_string, new_string}]  (targeted)
      - files: [{path, edits: [{old, new}]}]  (nested, flattened here)
    Returns unified {summary, files, edits}.
    """
    summary = str(proposal.get("summary") or "")
    files = list(proposal.get("files") or [])
    edits = list(proposal.get("edits") or [])
    if not files and not edits and isinstance(proposal.get("patch"), dict):
        inner = proposal["patch"]
        files = list(inner.get("files") or [])
        edits = list(inner.get("edits") or [])
        summary = summary or str(inner.get("summary") or "")

    flat_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        nested = item.get("edits")
        if isinstance(nested, list) and nested and item.get("content") is None:
            path = str(item.get("path") or "").replace("\\", "/")
            for edit in nested:
                if not isinstance(edit, dict):
                    continue
                edits.append(
                    {
                        "path": path,
                        "old_string": edit.get("old_string", edit.get("old", "")),
                        "new_string": edit.get("new_string", edit.get("new", "")),
                    }
                )
            continue
        flat_files.append(item)

    normalized_edits: list[dict[str, Any]] = []
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        normalized_edits.append(
            {
                "path": str(edit.get("path") or "").replace("\\", "/"),
                "old_string": str(edit.get("old_string", edit.get("old", ""))),
                "new_string": str(edit.get("new_string", edit.get("new", ""))),
            }
        )
    return {"summary": summary, "files": flat_files, "edits": normalized_edits}


def _line_rstrip(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n"))


def _locate_span(content: str, old: str, excerpt: str | None) -> tuple[int, int] | None:
    """Return (start, end) of `old` in `content`, or None if it cannot be placed safely."""
    if old == "":
        return None
    exact_count = content.count(old)
    if exact_count == 1:
        start = content.find(old)
        return start, start + len(old)
    if exact_count > 1 and excerpt:
        excerpt_at = content.find(excerpt) if excerpt and excerpt in content else -1
        if excerpt_at >= 0 and excerpt.count(old) == 1:
            rel = excerpt.find(old)
            if rel >= 0:
                start = excerpt_at + rel
                return start, start + len(old)
        # Excerpt may be a prefix/slice that appears once as a startswith region
        if excerpt and excerpt.count(old) == 1:
            rel = excerpt.find(old)
            if rel >= 0 and content.startswith(excerpt[: min(len(excerpt), 80)]):
                # prefix excerpt: first occurrence is the one the model saw
                if content.find(old) == rel:
                    return rel, rel + len(old)

    folded = _line_rstrip(content)
    folded_old = _line_rstrip(old)
    if folded_old and folded.count(folded_old) == 1:
        start = folded.find(folded_old)
        # Map folded index back only when lengths match per-line rstrip (approx via original scan)
        # Reconstruct by finding the first exact line-rstrip window.
        orig_lines = content.replace("\r\n", "\n").split("\n")
        old_lines = old.replace("\r\n", "\n").split("\n")
        old_norm = [ln.rstrip() for ln in old_lines]
        for i in range(0, len(orig_lines) - len(old_norm) + 1):
            window = [ln.rstrip() for ln in orig_lines[i : i + len(old_norm)]]
            if window == old_norm:
                prefix = "\n".join(orig_lines[:i])
                start = len(prefix) + (1 if i else 0)
                end = start + len("\n".join(orig_lines[i : i + len(old_norm)]))
                return start, end
    return None


def apply_edits_to_originals(
    edits: list[dict[str, Any]],
    originals: dict[str, str],
    excerpts: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Materialize full-file snapshots from targeted edits for existing apply pipeline."""
    working = dict(originals)
    changed: set[str] = set()
    excerpts = excerpts or {}
    for edit in edits:
        path = str(edit.get("path") or "").replace("\\", "/")
        old = str(edit.get("old_string", edit.get("old", "")))
        new = str(edit.get("new_string", edit.get("new", "")))
        if not path:
            continue
        current = working.get(path)
        if current is None:
            if old == "":
                working[path] = new
                changed.add(path)
            continue
        if old == "":
            # Explicit append: model is adding a new symbol at end of file.
            addition = new if new.startswith("\n") else "\n" + new
            working[path] = current.rstrip() + addition
            if not working[path].endswith("\n"):
                working[path] += "\n"
            changed.add(path)
            continue
        span = _locate_span(current, old, excerpts.get(path))
        if span is None:
            count = current.count(old)
            if count == 0:
                raise QualityGateError(
                    "edit_target_not_found",
                    "old_string was not found in the file; copy a verbatim unique snippet from context",
                    file=path,
                )
            raise QualityGateError(
                "edit_target_not_unique",
                f"old_string appears {count} times; include more surrounding lines so the match is unique",
                file=path,
                occurrences=count,
            )
        start, end = span
        working[path] = current[:start] + new + current[end:]
        changed.add(path)
    return [{"path": p, "content": working[p]} for p in changed]


def _top_level_names(source: str) -> set[str]:
    return set(_NAME_RE.findall(source or ""))


def patch_size_stats(original: str, proposed: str) -> dict[str, float | int]:
    orig_lines = original.splitlines()
    new_lines = proposed.splitlines()
    orig_set = set(orig_lines)
    kept = sum(1 for line in orig_lines if line in set(new_lines))
    deleted = max(0, len(orig_lines) - kept)
    return {
        "original_lines": len(orig_lines),
        "generated_lines": len(new_lines),
        "unchanged_lines": kept,
        "deleted_lines": deleted,
        "deletion_ratio": (deleted / len(orig_lines)) if orig_lines else 0.0,
    }


def destructive_rewrite_reason(original: str, proposed: str, path: str) -> str | None:
    """Return a reason if `proposed` looks like a stub/truncated replacement of `original`."""
    if not original:
        return None
    if path.endswith(".py"):
        try:
            ast.parse(proposed)
        except SyntaxError as error:
            return f"{path} Python syntax error: {error.msg} (line {error.lineno})"
    stats = patch_size_stats(original, proposed)
    if len(original) < 400:
        return None
    if len(proposed) < max(200, int(len(original) * 0.5)):
        return (
            f"{path} proposed content is much shorter than the original "
            f"({len(proposed)} vs {len(original)} chars; deletion_ratio={stats['deletion_ratio']:.2f})"
        )
    if stats["original_lines"] >= 20 and float(stats["deletion_ratio"]) >= 0.5:
        return (
            f"{path} dropped {stats['deleted_lines']}/{stats['original_lines']} lines "
            f"(deletion_ratio={stats['deletion_ratio']:.2f})"
        )
    dropped = _top_level_names(original) - _top_level_names(proposed)
    if dropped and (len(dropped) >= 2 or len(original) > 400):
        sample = ", ".join(sorted(dropped)[:6])
        return f"{path} dropped existing symbols: {sample}"
    return None


def materialize_safe_patch(
    proposal: dict[str, Any],
    originals: dict[str, str],
    excerpts: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Materialize a patch. Existing files should come from edits.
    Full-file bodies are allowed only for new paths, or for existing paths that
    are not destructive rewrites.
    """
    if proposal.get("truncated"):
        raise QualityGateError(
            "truncated_patch",
            "Truncated patch JSON; refusing partial full-file salvage. Use edits.",
        )
    norm = normalize_patch_proposal(proposal)
    by_path: dict[str, str] = {}
    errors: list[QualityGateError | ValueError] = []

    if norm["edits"]:
        try:
            for item in apply_edits_to_originals(norm["edits"], originals, excerpts=excerpts):
                by_path[item["path"]] = item["content"]
        except (QualityGateError, ValueError) as error:
            errors.append(error)

    for item in norm["files"]:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").replace("\\", "/")
        content = item.get("content")
        if not path or content is None:
            continue
        if Path(path).is_absolute() or ".." in Path(path).parts:
            continue
        proposed = str(content)
        original = originals.get(path)
        if original is not None:
            reason = destructive_rewrite_reason(original, proposed, path)
            if reason:
                stats = patch_size_stats(original, proposed)
                errors.append(
                    QualityGateError(
                        "destructive_rewrite",
                        reason,
                        file=path,
                        **stats,
                    )
                )
                continue
        by_path[path] = proposed

    if errors and not by_path:
        raise errors[0]
    if errors:
        raise errors[0]
    if not by_path:
        raise QualityGateError("missing_files_edits", "Invalid patch shape: missing files/edits")
    return [{"path": path, "content": body} for path, body in by_path.items()]


def prefer_targeted_files(
    proposal: dict[str, Any],
    originals: dict[str, str],
    excerpts: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Prefer edits when present; otherwise use full files.
    Returns list[{path, content}] suitable for CodeChangeTask.patch_json.
    """
    return materialize_safe_patch(proposal, originals, excerpts=excerpts)


def edit_prompt_addon() -> str:
    return (
        "For files already in context, return edits with exact old_string snippets "
        "(or empty old_string to append). Use files[] only for brand-new paths."
    )


__all__ = [
    "QualityGateError",
    "apply_edits_to_originals",
    "destructive_rewrite_reason",
    "edit_prompt_addon",
    "materialize_safe_patch",
    "normalize_patch_proposal",
    "patch_size_stats",
    "prefer_targeted_files",
]
