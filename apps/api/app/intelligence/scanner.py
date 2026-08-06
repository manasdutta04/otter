"""File tree scan — single pass."""
from __future__ import annotations

from pathlib import Path

from .types import IGNORED_DIRS

EXT_LANG = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".md": "Markdown",
    ".sql": "SQL",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".json": "JSON",
}


def list_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def language_counts(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        lang = EXT_LANG.get(path.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return counts


def read_text_capped(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""
