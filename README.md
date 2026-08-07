# Otter 🦦

Otter is an AI software engineer for modern teams — an engineering-intelligence platform that understands repositories, explains architecture, plans changes, reviews quality, and remembers project decisions.

**Understand → Explain → Plan → Review → Build (with approval).**

## Quickstart (self-host)

Same idea as platforms like [Archestra](https://archestra.ai/): pull/build with Docker, open the browser, bring your own model (Ollama on the host or any OpenAI-compatible API).

**Requires:** Docker Engine + Compose v2. **Recommended:** Ollama on the host (`ollama pull qwen2.5-coder:7b`).

```bash
cp .env.example .env
# Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
# OAuth callback: http://127.0.0.1:8000/auth/github/callback

docker compose -f docker/compose.platform.yml up --build -d
```

1. Open [http://127.0.0.1:3000/app/models](http://127.0.0.1:3000/app/models) and connect **Local Ollama** (or another free OpenAI-compatible endpoint).
2. Connect GitHub, then import a repository from `/app`.

Default stack = **one** Otter image (`otter/platform`) + official `postgres:16-alpine` + `redis:7-alpine`. Details: [docs/self-host.md](docs/self-host.md).

## Native development (no Docker)

Use when freeing RAM for Ollama on the host.

1. Copy `.env.example` → `.env` and set GitHub OAuth (use `localhost` URLs for native).
2. Start Ollama and pull models.
3. Local Postgres with user/db `otter` / `otter`.
4. Run:

```powershell
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"
powershell -ExecutionPolicy Bypass -File scripts/dev-native.ps1
```

Or manually:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+asyncpg://otter:otter@127.0.0.1:5432/otter"
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:REPOSITORY_DATA_DIR = "c:\Coding Workspace\veridexs\data\repositories"
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000

# second terminal
cd apps/web
npm install
npm run dev
```

## Contributor Docker (bind mounts)

```bash
docker compose -f docker/compose.dev.yml up --build
```

Not the product install path — use `compose.platform.yml` for self-host.

## Surfaces

| Surface | How to use |
|---------|------------|
| Web | Self-host UI at `http://127.0.0.1:3000` (`/app` workspace) |
| CLI | `npx otter` / `bunx otter` (same API) |
| MCP | `python apps/mcp/server.py` with `OTTER_API_URL` / `OTTER_SESSION` |
| VS Code | Extension in `apps/vscode` |
| GitHub App | Optional; `compose.dev.yml --profile github` |

## Product principles

- Explain before coding
- Approval before any write
- One API contract across all clients
- Grounded answers with source citations
- Self-host first; BYO local or remote LLM
