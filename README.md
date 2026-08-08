# Otter 🦦

**Self-hosted engineering intelligence** — understand repositories, plan changes, review quality, and ship patches with approval before any write.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![npm](https://img.shields.io/npm/v/@otter-engg/cli.svg)](https://www.npmjs.com/package/@otter-engg/cli)
[![Docker Hub](https://img.shields.io/docker/v/manasdutta04/otter?label=docker&logo=docker)](https://hub.docker.com/r/manasdutta04/otter)

**Site:** [otter.manasdutta.com](https://otter.manasdutta.com) · **Docs:** [otter.manasdutta.com/docs](https://otter.manasdutta.com/docs) · **Repo:** [github.com/manasdutta04/otter](https://github.com/manasdutta04/otter)

```
Understand → Explain → Plan → Approve → Build
```

**Current release:** [0.2.0](CHANGELOG.md) — engineer core in Docker Web/API + `@otter-engg/cli@0.2.0`. Docs: [otter.manasdutta.com/docs/changelog](https://otter.manasdutta.com/docs/changelog).

## Why Otter

Most AI coding tools jump straight to editing files. Otter starts with **understanding**: architecture signals, grounded chat with citations, plans with risks, then approval-gated patches and PRs. Repos and data stay on **your** machine.

## Quickstart

**Recommended:** [Ollama](https://ollama.com) on the host — `ollama pull qwen2.5-coder:7b`.

### Option A — Docker (full UI + API)

```bash
docker pull manasdutta04/otter
docker compose -f https://otter.manasdutta.com/docker-compose.yml up -d
```

Open [http://127.0.0.1:3000/app](http://127.0.0.1:3000/app) → **Connect GitHub** → Models → Import a repo.

> **Windows tip:** if Compose fails resolving `.env` from a URL, download [`docker-compose.yml`](https://otter.manasdutta.com/docker-compose.yml) first, then run `docker compose -f docker-compose.yml up -d`.

### Option B — CLI (no Docker)

```bash
npm i -g @otter-engg/cli   # or: pnpm add -g / yarn global add / bun add -g
otter
```

Then `/login`, `/model`, `/import owner/repo`, or type a freeform task. Data lives under `~/.otter/`.

pnpm, yarn, and bun install the **same** npm package — no separate registry publish.

## Surfaces

| Surface | How to use |
|---------|------------|
| **Web UI** | Docker stack → `http://127.0.0.1:3000/app` |
| **CLI** | [`@otter-engg/cli`](https://www.npmjs.com/package/@otter-engg/cli) → `otter` (CI: push `main` / tag `cli-v*`) |
| **Docs site** | [`apps/site`](apps/site) → [otter.manasdutta.com](https://otter.manasdutta.com) |
| **MCP** | [`apps/mcp`](apps/mcp) — stdio bridge to the local API |
| **GitHub App** | Connect via Otter App (Cloudflare auth broker) |

## Repository layout

```
apps/
  api/           FastAPI backend (+ packages/agent engineer core)
  web/           Product UI (Next.js) — served in Docker
  site/          Marketing + docs (Vercel)
  cli/           @otter-engg/cli
  auth-broker/   Cloudflare Worker for GitHub App login
  mcp/           MCP stdio server
  github-app/    Webhook service
packages/
  agent/         Shared engineer loop (Python) for API/Docker
docker/          Compose files (platform / dev)
docs/            Design notes for contributors
```

## Develop from source (contributor mode)

Prerequisites: Node 20+, Python 3.11+, Docker (optional), Postgres + Redis for native API, Ollama recommended.

```bash
git clone https://github.com/manasdutta04/otter.git
cd otter
cp .env.example .env   # contributor defaults — no production secrets
```

**Contributor Docker (bind mounts):**

```bash
docker compose -f docker/compose.dev.yml up --build
```

**Marketing site only:**

```bash
cd apps/site && npm install && npm run dev   # http://127.0.0.1:3001
```

**CLI package:**

```bash
cd apps/cli && npm install && npm run build
node dist/cli.js
```

**Native API + web** (see [CONTRIBUTING.md](CONTRIBUTING.md)):

```powershell
# Windows example
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"
powershell -ExecutionPolicy Bypass -File scripts/dev-native.ps1
```

## Contributing

Contributions are welcome — bugs, docs, UX, and features that support **understand → plan → approve → build**.

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Open an issue or draft PR describing the change
3. Keep PRs focused; add tests when you touch API/CLI behavior

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Security reports: [SECURITY.md](SECURITY.md).

## Product principles

- Explain before coding
- Approval before any write
- One contract across Web · CLI · MCP
- Grounded answers with source citations
- Self-host first; bring your own local or remote LLM

## License

[MIT](LICENSE) © Manas Dutta
