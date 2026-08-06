"""Framework detection from deps + paths."""
from __future__ import annotations

from pathlib import Path


def detect_frameworks(files: list[Path], dep_names: set[str], root: Path) -> list[str]:
    frameworks: list[str] = []
    rels = [str(p.relative_to(root)).replace("\\", "/").lower() for p in files]
    joined = " ".join(rels)

    if "next" in dep_names or any(r.startswith("app/") and r.endswith(("page.tsx", "page.ts", "layout.tsx")) for r in rels):
        frameworks.append("Next.js")
    if "express" in dep_names:
        frameworks.append("Express")
    if "fastify" in dep_names:
        frameworks.append("Fastify")
    if "vite" in dep_names or "vite.config.ts" in {p.name.lower() for p in files}:
        frameworks.append("Vite")
    if "react" in dep_names:
        frameworks.append("React")
    if "vue" in dep_names:
        frameworks.append("Vue")
    if "fastapi" in dep_names or any("from fastapi" in _peek(p) for p in files if p.suffix == ".py"):
        frameworks.append("FastAPI")
    if "flask" in dep_names:
        frameworks.append("Flask")
    if "django" in dep_names or any(p.name == "manage.py" for p in files):
        frameworks.append("Django")
    if "drizzle-orm" in dep_names:
        frameworks.append("Drizzle ORM")
    if "prisma" in dep_names or any(p.name == "schema.prisma" for p in files):
        frameworks.append("Prisma")
    if "mongoose" in dep_names:
        frameworks.append("Mongoose")
    if "sqlalchemy" in dep_names:
        frameworks.append("SQLAlchemy")
    if "passport" in dep_names or "next-auth" in dep_names or "@auth/core" in dep_names:
        frameworks.append("Auth library present")
    if "docker" in joined or any(p.name.lower() in {"dockerfile", "compose.yml", "docker-compose.yml"} for p in files):
        frameworks.append("Docker")

    return sorted(set(frameworks))


def _peek(path: Path, n: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:n].lower()
    except OSError:
        return ""
