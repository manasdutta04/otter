# Otter 🦦

Otter is an engineering-intelligence platform: understand repositories, explain architecture, plan changes, review quality, and remember project decisions — with approval before any write.

**Understand → Explain → Plan → Review → Build (with approval).**

## Surfaces

| Surface | Package | Where it runs |
|---------|---------|---------------|
| **Marketing + docs** | [`apps/site`](apps/site) | Vercel (public domain) |
| **Product UI + API** | [`apps/web`](apps/web) + [`apps/api`](apps/api) | Docker on your machine |
| **CLI** | [`@otter-engg/cli`](https://www.npmjs.com/package/@otter-engg/cli) | Local Node (≥20); `~/.otter/` |

The landing page is **not** inside Docker. After compose up, open `http://127.0.0.1:3000/app`.

## Quickstart

**Recommended:** Ollama on the host (`ollama pull qwen2.5-coder:7b`).

### Docker (full UI)

```bash
docker pull manasdutta04/otter
docker compose -f https://YOUR_SITE/docker-compose.yml up -d
```

Image: [`manasdutta04/otter`](https://hub.docker.com/r/manasdutta04/otter). Compose creates **local** Postgres + Redis.

### CLI (no Docker)

```bash
npm i @otter-engg/cli
otter
```

Bun installs the same npm package (`bun add -g @otter-engg/cli`) — no separate Bun publish.

Connect GitHub via the **Otter GitHub App** (Cloudflare auth broker — see `apps/auth-broker/`).

1. Docker: open [http://127.0.0.1:3000/app](http://127.0.0.1:3000/app) → **Connect GitHub**. CLI: `otter login`.
2. Point models at **Local Ollama** (or OpenAI-compatible).
3. Import a repository.

Details: public docs from `apps/site` (`/docs`).
## Marketing site (Vercel)

```bash
cd apps/site
npm install
npm run dev   # http://127.0.0.1:3001
```

Deploy: create a Vercel project with **Root Directory** `apps/site`. Set `NEXT_PUBLIC_APP_URL=http://127.0.0.1:3000` (or your users’ local/default app URL).

## Native development (no Docker)

1. Copy `.env.example` → `.env` and set GitHub OAuth.
2. Start Ollama and pull models.
3. Local Postgres with user/db `otter` / `otter`.
4. Run:

```powershell
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"
powershell -ExecutionPolicy Bypass -File scripts/dev-native.ps1
```

Or manually run API (`apps/api`) and product web (`apps/web`). Marketing site is optional: `apps/site` on port 3001.

## Contributor Docker (bind mounts)

```bash
docker compose -f docker/compose.dev.yml up --build
```

Not the product install path — use `compose.platform.yml` for self-host.

## Client surfaces

| Surface | How to use |
|---------|------------|
| Web (product) | Self-host UI at `http://127.0.0.1:3000/app` |
| Site (docs) | Vercel / `apps/site` |
| CLI | `npm i @otter-engg/cli` → `otter` — local `~/.otter/`, no Docker |
| MCP | `python apps/mcp/server.py` (Docker API + session; optional) |
| VS Code | Extension in `apps/vscode` |

## Product principles

- Explain before coding
- Approval before any write
- One API contract across all clients
- Grounded answers with source citations
- Self-host first; BYO local or remote LLM
