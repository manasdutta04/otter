from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from collections.abc import Iterable

DEFAULT_IGNORED = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv"}
DEFAULT_SCORE_BOOSTS = {
    "authentication": ["auth", "login", "session", "token", "oauth", "jwt", "middleware"],
    "api": ["api", "route", "endpoint", "handler", "controller", "server"],
    "database": ["db", "database", "migration", "schema", "model", "repository"],
    "review": ["review", "lint", "test", "spec", "quality"],
    "planning": ["plan", "planner", "task", "roadmap", "implementation"],
    "memory": ["memory", "decision", "convention", "note"],
}

@dataclass(frozen=True)
class RetrievalHit:
    path: str
    score: float
    reason: str
    preview: str | None = None


class RepositoryRetrievalIndex:
    def __init__(self, root: Path, ignored: set[str] | None = None) -> None:
        self.root = root
        self.ignored = ignored or DEFAULT_IGNORED
        self.files = [path for path in root.rglob("*") if path.is_file() and not any(part in self.ignored for part in path.parts)]

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.root)).replace("\\", "/")

    def _preview(self, path: Path) -> str | None:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        lines = [line.strip() for line in content.splitlines() if line.strip()][:4]
        if not lines:
            return None
        return " ".join(lines)[:240]

    def _score_for_terms(self, path: Path, content: str, terms: list[str]) -> tuple[float, str]:
        relative = self._relative(path)
        score = 0.0
        reasons: list[str] = []
        lowered_relative = relative.lower()
        lowered_name = path.name.lower()
        lowered_content = content.lower()
        for term in terms:
            if term in lowered_relative:
                score += 5
                reasons.append(f"path match: {term}")
            if term in lowered_name:
                score += 4
                reasons.append(f"filename match: {term}")
            if term in lowered_content:
                score += 2
                reasons.append(f"content match: {term}")
        if any(keyword in lowered_content for keyword in ["auth", "login", "session", "token", "oauth", "jwt"]):
            score += 1.5
        return score, ", ".join(dict.fromkeys(reasons)) or "filename and content analysis"

    def search(self, query: str, *, limit: int = 8) -> list[RetrievalHit]:
        terms = [term for term in re.split(r"[^a-zA-Z0-9]+", query.lower()) if len(term) > 2]
        if not terms:
            return []
        query_boosts = [keyword for key, keywords in DEFAULT_SCORE_BOOSTS.items() if key in query.lower() for keyword in keywords]
        hits: list[RetrievalHit] = []
        for path in self.files:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")[:100000]
            except OSError:
                continue
            score, reason = self._score_for_terms(path, content, terms + query_boosts)
            if score <= 0:
                continue
            hits.append(RetrievalHit(path=self._relative(path), score=score, reason=reason, preview=self._preview(path)))
        hits.sort(key=lambda item: (item.score, -len(item.path)), reverse=True)
        return hits[:limit]

    def list_entry_points(self) -> list[str]:
        entry_names = {"main.py", "app.py", "server.py", "index.ts", "index.tsx", "main.ts", "main.tsx", "manage.py"}
        return [self._relative(path) for path in self.files if path.name.lower() in entry_names][:30]

    def list_files(self) -> list[str]:
        return [self._relative(path) for path in self.files]

    def list_folders(self, limit: int = 80) -> list[str]:
        folders = sorted({self._relative(path.parent) for path in self.files if path.parent != self.root})
        return folders[:limit]


def answer_repository_question(root: Path, question: str, *, limit: int = 6) -> dict[str, object]:
    index = RepositoryRetrievalIndex(root)
    hits = index.search(question, limit=limit)
    lowered = question.lower()
    if not hits:
        return {
            "answer": "I could not find a grounded source match for that question yet.",
            "sources": [],
        }

    if any(term in lowered for term in ["auth", "login", "session", "oauth", "jwt", "token"]):
        lead = "Authentication-related files and nearby implementation details look most relevant."
    elif any(term in lowered for term in ["folder", "structure", "architecture", "layout"]):
        lead = "The most relevant structural files and folders are listed below."
    elif any(term in lowered for term in ["plan", "planning", "roadmap", "implementation"]):
        lead = "Planning-related files and task surfaces appear to be the closest match."
    elif any(term in lowered for term in ["health", "review", "security", "performance"]):
        lead = "Quality and health surfaces appear to be the strongest matches."
    else:
        lead = "I found these likely relevant files and snippets."

    sources = []
    for hit in hits:
        source: dict[str, object] = {"path": hit.path, "reason": hit.reason, "score": hit.score}
        if hit.preview:
            source["preview"] = hit.preview
        sources.append(source)

    answer_lines = [lead]
    for hit in hits[:3]:
        snippet = f"{hit.path} ({hit.reason})"
        if hit.preview:
            snippet = f"{snippet}: {hit.preview}"
        answer_lines.append(f"- {snippet}")

    return {"answer": "\n".join(answer_lines), "sources": sources}
