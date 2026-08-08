# Otter 🦦

Otter is an engineering-intelligence platform: understand repositories, explain architecture, plan changes, review quality, and remember project decisions — with approval before any write.

**Understand → Explain → Plan → Review → Build (with approval).**

## Two surfaces

| Surface | Package | Where it runs |
|---------|---------|---------------|
| **Marketing + docs** | [`apps/site`](apps/site) | Vercel (public domain) |
| **Product UI + API** | [`apps/web`](apps/web) + [`apps/api`](apps/api) | Docker on your machine |

The landing page is **not** inside Docker. After `compose up`, open `http://127.0.0.1:3000/app`.

## Quickstart (self-host)

**Requires:** Docker Engine + Compose v2. **Recommended:** Ollama on the host (`ollama pull qwen2.5-coder:7b`).

```bash
docker compose -f https://YOUR_SITE/docker-compose.yml up -d
```

No clone required. Image: [`manasdutta04/otter`](https://hub.docker.com/r/manasdutta04/otter). Compose creates **local** Postgres + Redis. Connect GitHub via the **Otter GitHub App** (Cloudflare auth broker — see `apps/auth-broker/`).

Standalone CLI (no Docker): `npm install -g otter-engg` then `otter login` — see `/docs/cli`.

1. Open [http://127.0.0.1:3000/app](http://127.0.0.1:3000/app) → **Connect GitHub**.
2. Open Models and connect **Local Ollama**.
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

## Surfaces

| Surface | How to use |
|---------|------------|
| Web (product) | Self-host UI at `http://127.0.0.1:3000/app` |
| Site (docs) | Vercel / `apps/site` |
| CLI | Standalone `otter-engg` (`otter` bin) — local `.otter` storage, no Docker |
| MCP | `python apps/mcp/server.py` (Docker API + session; optional) |
| VS Code | Extension in `apps/vscode` |

## Product principles

- Explain before coding
- Approval before any write
- One API contract across all clients
- Grounded answers with source citations
- Self-host first; BYO local or remote LLM
