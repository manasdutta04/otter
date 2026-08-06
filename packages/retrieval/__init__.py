"""
Code chunking, TF-IDF + keyword hybrid indexing, and grounded semantic retrieval for Otter repositories.
"""
from __future__ import annotations

from pathlib import Path
import math
import re
from collections import Counter

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build", ".turbo"}
ALLOWED_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml",
    ".sql", ".sh", ".go", ".rs", ".java", ".kt", ".dockerfile",
}
NAME_ALLOW = {"Dockerfile", "Makefile", "AGENTS.md", "CLAUDE.md"}

_INDEX_CACHE: dict[str, "RepositorySemanticIndex"] = {}


def is_text_file(path: Path) -> bool:
    if path.name in NAME_ALLOW:
        return True
    if path.name.startswith(".") and path.name not in {".env.example", ".gitignore"}:
        return False
    return path.suffix.lower() in ALLOWED_EXTS


def chunk_file(file_path: Path, repo_root: Path, chunk_size: int = 40, overlap: int = 10) -> list[dict]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines = content.splitlines()
    if not lines:
        return []
    rel_path = file_path.relative_to(repo_root).as_posix()
    chunks: list[dict] = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(lines), step):
        chunk_lines = lines[i : i + chunk_size]
        if not chunk_lines:
            continue
        chunks.append(
            {
                "rel_path": rel_path,
                "start_line": i + 1,
                "end_line": i + len(chunk_lines),
                "content": "\n".join(chunk_lines),
                "file_name": file_path.name,
            }
        )
    return chunks


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_]+", text)
    tokens: list[str] = []
    for w in words:
        sub = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", w).lower().split("_")
        for s in sub:
            tokens.extend(part for part in s.split() if len(part) > 1)
    return tokens


class RepositorySemanticIndex:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.chunks: list[dict] = []
        self.doc_freqs: Counter = Counter()
        self.num_docs = 0
        self._build_index()

    def _build_index(self) -> None:
        all_chunks: list[dict] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file() or any(part in IGNORE_DIRS for part in path.parts):
                continue
            if is_text_file(path):
                all_chunks.extend(chunk_file(path, self.repo_root))
        self.chunks = all_chunks
        self.num_docs = len(all_chunks)
        for chunk in all_chunks:
            token_list = tokenize(f"{chunk['content']} {chunk['rel_path']} {chunk['file_name']}")
            chunk["tokens"] = Counter(token_list)
            for token in set(token_list):
                self.doc_freqs[token] += 1

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens or self.num_docs == 0:
            return []
        query_lower = query.lower()
        scores: list[tuple[float, int]] = []
        for idx, chunk in enumerate(self.chunks):
            score = 0.0
            rel = chunk["rel_path"].lower()
            name = chunk["file_name"].lower()
            for qt in query_tokens:
                if qt in name:
                    score += 12.0
                elif qt in rel:
                    score += 7.0
            # Intent boosts for common engineering questions
            if "agent" in query_lower and ("agent" in rel or "agents" in rel):
                score += 15.0
            if "auth" in query_lower and any(term in rel for term in ("auth", "session", "oauth", "login")):
                score += 10.0
            if any(term in query_lower for term in ("solana", "wallet", "connection", "connect")):
                if any(term in rel for term in ("solana", "wallet", "connect", "provider", "adapter")):
                    score += 16.0
                if Path(chunk["rel_path"]).suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".py"}:
                    score += 4.0
                if chunk["file_name"].lower().startswith("readme"):
                    score -= 6.0
            chunk_tokens: Counter = chunk["tokens"]
            chunk_len = sum(chunk_tokens.values()) or 1
            for qt in query_tokens:
                if qt in chunk_tokens:
                    tf = chunk_tokens[qt] / chunk_len
                    df = self.doc_freqs.get(qt, 1)
                    idf = math.log((self.num_docs + 1) / df) + 1.0
                    score += tf * idf * 10.0
            if score > 0:
                scores.append((score, idx))
        scores.sort(key=lambda item: item[0], reverse=True)
        results: list[dict] = []
        for score, idx in scores[:top_k]:
            hit = dict(self.chunks[idx])
            hit["score"] = score
            results.append(hit)
        return results


def get_index(repo_root: Path) -> RepositorySemanticIndex:
    key = str(repo_root.resolve())
    cached = _INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    index = RepositorySemanticIndex(repo_root)
    _INDEX_CACHE[key] = index
    return index


def clear_index_cache(repo_root: Path | None = None) -> None:
    if repo_root is None:
        _INDEX_CACHE.clear()
        return
    _INDEX_CACHE.pop(str(repo_root.resolve()), None)


def _plain_excerpt(content: str, max_lines: int = 10) -> str:
    """Strip markdown noise so excerpts read like normal text."""
    cleaned: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        line = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*]\s+", "• ", line)
        line = re.sub(r"^\d+\.\s+", "", line)
        line = line.replace("**", "").replace("__", "").replace("*", "")
        if line:
            cleaned.append(line)
        if len(cleaned) >= max_lines:
            break
    return "\n".join(cleaned)


def _pick_primary(question: str, results: list[dict]) -> dict:
    q = question.lower()
    code_exts = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java"}
    wants_implementation = any(
        term in q
        for term in ("connection", "connect", "wallet", "auth", "api", "hook", "component", "service", "client", "provider")
    )
    if wants_implementation:
        code_hits = [
            hit
            for hit in results
            if Path(hit["rel_path"]).suffix.lower() in code_exts
            or any(term in hit["rel_path"].lower() for term in ("connect", "wallet", "solana", "auth", "provider", "client"))
        ]
        if code_hits:
            return code_hits[0]
    if "agent" in q:
        agent_hits = [hit for hit in results if "agent" in hit["rel_path"].lower()]
        if agent_hits:
            return agent_hits[0]
    return results[0]


def _natural_answer(question: str, primary: dict, others: list[dict]) -> str:
    path = primary["rel_path"]
    start = primary["start_line"]
    end = primary["end_line"]
    q = question.lower().strip().rstrip("?")

    if any(term in q for term in ("where", "which file", "what file", "find")):
        lead = f"Look at `{path}` (around lines {start}–{end})."
    elif any(term in q for term in ("how", "explain", "tell me", "about")):
        lead = f"`{path}` is the best place to start for this — lines {start}–{end}."
    else:
        lead = f"The most relevant place in this repo is `{path}` (lines {start}–{end})."

    if others:
        related = ", ".join(f"`{hit['rel_path']}`" for hit in others[:3])
        return f"{lead}\n\nAlso worth checking: {related}."
    return lead


def answer_repository_question(repo_root: Path, question: str) -> dict:
    """Retrieve grounded chunks and answer like a teammate, with citations."""
    index = get_index(Path(repo_root))
    results = index.search(question, top_k=8)
    if not results:
        return {
            "answer": (
                "I couldn’t find a strong match for that in the repo. "
                "Try naming a file, folder, or symbol — for example “solana wallet connection” or “auth middleware”."
            ),
            "sources": [],
        }

    primary = _pick_primary(question, results)
    others = [
        hit
        for hit in results
        if not (hit["rel_path"] == primary["rel_path"] and hit["start_line"] == primary["start_line"])
    ]
    # Deduplicate by path for related list
    seen: set[str] = {primary["rel_path"]}
    unique_others: list[dict] = []
    for hit in others:
        if hit["rel_path"] in seen:
            continue
        seen.add(hit["rel_path"])
        unique_others.append(hit)
        if len(unique_others) >= 3:
            break

    sources = [
        {
            "path": f"{hit['rel_path']}:L{hit['start_line']}-{hit['end_line']}",
            "start_line": hit["start_line"],
            "end_line": hit["end_line"],
        }
        for hit in [primary, *unique_others]
    ]
    return {
        "answer": _natural_answer(question, primary, unique_others),
        "sources": sources,
        "primary_file": primary["rel_path"],
        "primary_lines": f"L{primary['start_line']}-{primary['end_line']}",
        "excerpt": _plain_excerpt(primary["content"]),
    }
