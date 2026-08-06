"""
Code chunking, TF-IDF + Keyword Hybrid Indexing, and Grounded Semantic Retrieval for veridexs repositories.
"""
from pathlib import Path
import re
import math
from collections import Counter

IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build"}
ALLOWED_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml", ".sql", ".sh", ".dockerfile", "Dockerfile"}

def is_text_file(path: Path) -> bool:
    if path.name.startswith(".") and path.name != ".env.example":
        return False
    return path.suffix.lower() in ALLOWED_EXTS or path.name in ALLOWED_EXTS

def chunk_file(file_path: Path, repo_root: Path, chunk_size: int = 40, overlap: int = 10) -> list[dict]:
    """Break a file into line-aware chunks with line numbers and metadata."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = content.splitlines()
    if not lines:
        return []

    rel_path = file_path.relative_to(repo_root).as_posix()
    chunks = []
    
    # Simple line window chunking with line number tracking
    step = max(1, chunk_size - overlap)
    for i in range(0, len(lines), step):
        chunk_lines = lines[i : i + chunk_size]
        if not chunk_lines:
            continue
        chunk_text = "\n".join(chunk_lines)
        start_line = i + 1
        end_line = i + len(chunk_lines)
        chunks.append({
            "rel_path": rel_path,
            "start_line": start_line,
            "end_line": end_line,
            "content": chunk_text,
            "file_name": file_path.name
        })
    return chunks

def tokenize(text: str) -> list[str]:
    """Tokenize code/text splitting camelCase, snake_case, and words."""
    words = re.findall(r"[A-Za-z0-9_]+", text)
    tokens = []
    for w in words:
        # Split camelCase & snake_case
        sub = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", w).lower().split("_")
        for s in sub:
            tokens.extend(s.split())
    return [t for t in tokens if len(t) > 1]

class RepositorySemanticIndex:
    """In-memory hybrid retrieval index for a repository."""
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.chunks: list[dict] = []
        self.doc_freqs: Counter = Counter()
        self.num_docs = 0
        self._build_index()

    def _build_index(self):
        all_chunks = []
        for p in self.repo_root.rglob("*"):
            if p.is_file() and not any(part in IGNORE_DIRS for part in p.parts):
                if is_text_file(p):
                    all_chunks.extend(chunk_file(p, self.repo_root))

        self.chunks = all_chunks
        self.num_docs = len(all_chunks)
        for chunk in all_chunks:
            tokens = set(tokenize(chunk["content"] + " " + chunk["rel_path"]))
            chunk["tokens"] = Counter(tokenize(chunk["content"] + " " + chunk["rel_path"]))
            for t in tokens:
                self.doc_freqs[t] += 1

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens or self.num_docs == 0:
            return []

        scores = []
        for idx, chunk in enumerate(self.chunks):
            score = 0.0
            # Path matching bonus
            query_lower = query.lower()
            if any(qt in chunk["rel_path"].lower() for qt in query_tokens):
                score += 5.0

            # TF-IDF BM25-like scoring
            chunk_tokens = chunk["tokens"]
            chunk_len = sum(chunk_tokens.values())
            if chunk_len == 0:
                continue

            for qt in query_tokens:
                if qt in chunk_tokens:
                    tf = chunk_tokens[qt] / chunk_len
                    df = self.doc_freqs.get(qt, 1)
                    idf = math.log((self.num_docs + 1) / df) + 1.0
                    score += tf * idf * 10.0

            if score > 0:
                scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            c = dict(self.chunks[idx])
            c["score"] = score
            results.append(c)
        return results

def answer_repository_question(repo_root: Path, question: str) -> dict:
    """Retrieve grounded chunks from repository and synthesize answer with source citations."""
    index = RepositorySemanticIndex(repo_root)
    results = index.search(question, top_k=5)

    if not results:
        return {
            "answer": f"I analyzed the repository for '{question}', but found no directly relevant source code or documentation snippets.",
            "sources": []
        }

    sources = []
    snippets_text = []
    for res in results:
        cit = f"{res['rel_path']}:L{res['start_line']}-{res['end_line']}"
        sources.append({"path": cit, "start_line": res["start_line"], "end_line": res["end_line"]})
        snippets_text.append(f"### Source: `{cit}`\n```\n{res['content']}\n```")

    joined_snippets = "\n\n".join(snippets_text)
    answer = f"Based on repository analysis for '{question}', here are the relevant implementations and architecture details:\n\n{joined_snippets}"
    return {
        "answer": answer,
        "sources": sources
    }
