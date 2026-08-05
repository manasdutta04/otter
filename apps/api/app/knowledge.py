import json
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from .models import GeneratedDocument, MemoryEntry, RepositoryGraph, RepositoryIntelligence

async def add_memory(db: AsyncSession, repository_id: str, user_id: str, kind: str, title: str, content: str) -> MemoryEntry:
    entry = MemoryEntry(id=uuid4().hex[:12], repository_id=repository_id, user_id=user_id, kind=kind, title=title, content=content)
    db.add(entry); await db.commit(); await db.refresh(entry); return entry

async def generate_overview(db: AsyncSession, repository_id: str, user_id: str, repository_name: str) -> GeneratedDocument:
    intelligence = await db.get(RepositoryIntelligence, repository_id)
    graph = await db.get(RepositoryGraph, repository_id)
    tech = json.loads(intelligence.tech_stack) if intelligence else []
    folders = json.loads(intelligence.folders) if intelligence else []
    entries = json.loads(intelligence.entry_points) if intelligence else []
    signals = json.loads(intelligence.architecture_signals) if intelligence else []
    nodes = json.loads(graph.nodes) if graph else []
    edges = json.loads(graph.edges) if graph else []
    content = "\n".join([
        f"# {repository_name} — Engineering Overview",
        "",
        intelligence.summary if intelligence else "Repository intelligence is not available yet.",
        "",
        "## Technology stack",
        "\n".join(f"- {item}" for item in tech) or "- Not detected",
        "",
        "## Repository structure",
        "\n".join(f"- `{item}`" for item in folders[:30]) or "- No nested folders detected",
        "",
        "## Entry points",
        "\n".join(f"- `{item}`" for item in entries) or "- No conventional entry points detected",
        "",
        "## Architecture signals",
        "\n".join(f"- {item}" for item in signals) or "- No additional signals detected",
        "",
        f"## Graph coverage\n- {len(nodes)} nodes\n- {len(edges)} relationships",
    ])
    document = GeneratedDocument(id=uuid4().hex[:12], repository_id=repository_id, user_id=user_id, kind="overview", title=f"{repository_name} Engineering Overview", content=content, created_at=datetime.now(timezone.utc))
    db.add(document); await db.commit(); await db.refresh(document); return document
