# Contributing to Otter

Thanks for helping make Otter better. This repo is public and MIT-licensed — issues, docs fixes, and PRs are welcome.

## Before you start

1. Skim the [README](README.md) and public docs: https://otter.manasdutta.com/docs
2. Search [existing issues](https://github.com/manasdutta04/otter/issues) to avoid duplicates
3. For large features, open an issue first so we can align on scope

**Fit the product:** Otter is *understand → explain → plan → review → build (with approval)*. Prefer changes that strengthen repository understanding, planning, quality, or developer productivity. Avoid silent code mutation, generic chatbot chrome, or features that fight the self-host / BYO-model model.

## Ways to contribute

| Area | Examples |
|------|----------|
| Docs | Site pages under `apps/site/app/docs`, root README, app READMEs |
| CLI | `apps/cli` — slash commands, UX, install story |
| Web UI | `apps/web` — product experience at `/app` |
| API | `apps/api` — FastAPI routes and domain logic |
| Infra | Docker compose, auth broker, CI |
| Extensions | `apps/mcp`, `apps/vscode` |

## Development setup

### Prerequisites

- Node.js **20+**
- Python **3.11+** (API / MCP)
- Docker Desktop or Engine + Compose v2 (optional but easiest for full stack)
- [Ollama](https://ollama.com) recommended: `ollama pull qwen2.5-coder:7b`

### Clone (contributor mode)

```bash
git clone https://github.com/manasdutta04/otter.git
cd otter
cp .env.example .env
```

`.env.example` is for **contributor / developer mode** only (local API, web, docs). Leave secrets blank — Connect GitHub can use the public auth broker URL already set there. Never put production Client Secrets, redeem secrets, or npm tokens in git.

Fill GitHub App / broker operator values only if you are deploying your own Worker. Most local UI and CLI work against Ollama does not need them.

### Full stack (Docker, bind mounts)

```bash
docker compose -f docker/compose.dev.yml up --build
```

Product UI: http://127.0.0.1:3000/app

### Marketing / docs site

```bash
cd apps/site
npm install
npm run dev
```

http://127.0.0.1:3001 — this is what deploys to Vercel (`otter.manasdutta.com`).

### CLI

```bash
cd apps/cli
npm install
npm run build
node dist/cli.js
# or: npm run dev
```

Package name on npm: `@otter-engg/cli` (binary `otter`).

### Native API + web (no Docker)

1. Postgres with user/db `otter` / `otter`, and Redis
2. Adjust `.env` (`DATABASE_URL`, `REDIS_URL`, `LLM_BASE_URL`)
3. Run:

```powershell
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"
powershell -ExecutionPolicy Bypass -File scripts/dev-native.ps1
```

Or start `apps/api` (uvicorn) and `apps/web` (`npm run dev`) yourself.

## Pull request checklist

- [ ] Focused change (one concern per PR when possible)
- [ ] Docs or comments updated if behavior / public commands change
- [ ] CLI: `npm run build` in `apps/cli` succeeds
- [ ] Site: `npx tsc --noEmit` in `apps/site` if you touched the marketing app
- [ ] No secrets, tokens, or local `.env` contents committed
- [ ] Clear PR description: *why* + how to test

## Commit / PR style

- Prefer short, imperative summaries: `fix CLI create PR path`, `docs: clarify Docker Windows compose`
- Link related issues
- Screenshots or terminal recordings help for UI / CLI UX changes

## Code of conduct & security

- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Vulnerability reports: [SECURITY.md](SECURITY.md) — do **not** open a public issue for sensitive reports

## Maintainers / operators

GitHub App credentials and the Cloudflare auth broker live outside the Docker image. See `apps/auth-broker/` and `/docs/github` on the site. Never commit Client Secrets or broker tokens.

## Questions

Open a GitHub Discussion or Issue with the `question` label. Thanks for contributing 🦦
