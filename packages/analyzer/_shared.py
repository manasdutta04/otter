from __future__ import annotations

from pathlib import Path

DEFAULT_IGNORED = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv"}
MANIFESTS = {"package.json": "Node.js", "requirements.txt": "Python", "pyproject.toml": "Python", "go.mod": "Go", "Cargo.toml": "Rust", "pom.xml": "Java", "docker-compose.yml": "Docker"}


def contains_text(root: Path, tokens: list[str]) -> bool:
    lowered_tokens = [token.lower() for token in tokens]
    for path in root.rglob("*"):
        if not path.is_file() or any(part in DEFAULT_IGNORED for part in path.parts):
            continue
        relative = str(path.relative_to(root)).lower()
        if any(token in relative for token in lowered_tokens):
            return True
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
        except OSError:
            continue
        if any(token in content for token in lowered_tokens):
            return True
    return False
