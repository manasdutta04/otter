"""Database / ORM detection."""
from __future__ import annotations

import re
from pathlib import Path

from .scanner import read_text_capped
from .types import DatabaseSignal

PGTABLE = re.compile(r"""pgTable\s*\(\s*['"]([^'"]+)['"]""")
PRISMA_MODEL = re.compile(r"^\s*model\s+(\w+)\s*\{", re.MULTILINE)


def detect_databases(root: Path, files: list[Path], dep_names: set[str]) -> list[DatabaseSignal]:
    signals: list[DatabaseSignal] = []
    drizzle_files: list[str] = []
    drizzle_tables: list[str] = []
    prisma_files: list[str] = []
    prisma_models: list[str] = []
    sqla_files: list[str] = []
    mongoose_files: list[str] = []

    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        text = ""
        if path.suffix.lower() in {".ts", ".tsx", ".js", ".py", ".prisma"} or path.name.endswith(".prisma"):
            text = read_text_capped(path, 80_000)
        if not text:
            continue
        if "drizzle-orm" in text or "pgTable" in text:
            drizzle_files.append(rel)
            drizzle_tables.extend(PGTABLE.findall(text))
        if path.name == "schema.prisma" or "prisma" in rel.lower():
            prisma_files.append(rel)
            prisma_models.extend(PRISMA_MODEL.findall(text))
        if "sqlalchemy" in text.lower() or "__tablename__" in text:
            sqla_files.append(rel)
        if "mongoose" in text or ("Schema(" in text and "mongoose" in dep_names):
            mongoose_files.append(rel)

    if drizzle_files or "drizzle-orm" in dep_names:
        evidence = "pgTable: " + ", ".join(sorted(set(drizzle_tables))[:12]) if drizzle_tables else "drizzle-orm dependency / imports"
        signals.append(DatabaseSignal(orm="drizzle", evidence=evidence, files=sorted(set(drizzle_files))[:20]))
    if prisma_files or "prisma" in dep_names:
        evidence = "models: " + ", ".join(sorted(set(prisma_models))[:12]) if prisma_models else "Prisma schema/dependency"
        signals.append(DatabaseSignal(orm="prisma", evidence=evidence, files=sorted(set(prisma_files))[:20]))
    if sqla_files or "sqlalchemy" in dep_names:
        signals.append(DatabaseSignal(orm="sqlalchemy", evidence="SQLAlchemy models/tables", files=sorted(set(sqla_files))[:20]))
    if mongoose_files or "mongoose" in dep_names:
        signals.append(DatabaseSignal(orm="mongoose", evidence="Mongoose schemas", files=sorted(set(mongoose_files))[:20]))
    if "pg" in dep_names or "postgres" in dep_names or "asyncpg" in dep_names:
        signals.append(DatabaseSignal(orm="postgres-client", evidence="PostgreSQL client dependency", files=[]))

    return signals
