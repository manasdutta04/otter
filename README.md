# Otter 🦦

Otter is an AI software engineer for modern teams — an engineering-intelligence platform that understands repositories, explains architecture, plans changes, reviews quality, and remembers project decisions.

**Understand → Explain → Plan → Review → Build (with approval).**

## Local development

1. Copy `.env.example` to `.env`.
2. Create a GitHub OAuth App with callback `http://localhost:8000/auth/github/callback` and fill in credentials.
3. Run `docker compose -f docker/compose.yml up --build`.
4. Open [http://localhost:3000](http://localhost:3000).

If you previously ran this stack as `veridexs`, reset the Postgres volume once so the `otter` role is created:

```powershell
docker compose -f docker/compose.yml down
docker volume rm docker_postgres_data
docker compose -f docker/compose.yml up --build
```

## Surfaces

| Surface | How to use |
|---------|------------|
| Web | Marketing at `/`, workspace at `/app` |
| CLI | `npx otter` / `bunx otter` (see `apps/cli`) |
| MCP | `python apps/mcp/server.py` with `OTTER_API_URL` / `OTTER_SESSION` |
| VS Code | Extension in `apps/vscode` |
| GitHub App | Webhooks on port `9000` |

## Product principles

- Explain before coding
- Approval before any write
- One API contract across all clients
- Grounded answers with source citations
