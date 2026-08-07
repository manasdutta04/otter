# Otter Deployment Guide

Self-host topology (default): **one** `manasdutta04/otter` container (API + web + worker) from Docker Hub, plus official PostgreSQL and Redis (local volumes). Ollama/LLM stays on the host or a remote OpenAI-compatible endpoint.

GitHub Connect uses the **Otter GitHub App** via a Cloudflare Worker (`apps/auth-broker`). App client secrets stay in Cloudflare Secrets — never in Docker Hub.

## Requirements

- Product install: public `/docker-compose.yml` on the marketing site, or `docker/compose.platform.yml`.
- Set `OTTER_AUTH_BROKER_URL` (and matching `OTTER_AUTH_REDEEM_SECRET` if the Worker requires it). See `apps/auth-broker/README.md`.
- Contributor bind-mounts: `docker/compose.dev.yml` (optional local `GITHUB_CLIENT_*` without broker).
- Platform image runs `alembic upgrade head` on boot; do not skip migrations.
- Persist PostgreSQL and `repository_data` volumes.
- Health checks: API `/health`, web HTTP 200 on `:3000`.

## Release safety

Deploy progressively, verify import jobs and queues (Redis), and keep a rollback path (previous image tag) for each release.

## Surfaces after deploy

- Web: marketing site + workspace `/app` on Docker `:3000`
- CLI: `otter login` against `OTTER_API_URL` (Docker API must be running)
- MCP: same session as CLI (`~/.otter/config.json` or `OTTER_SESSION`)
- Auth broker: Cloudflare only for Connect; day-to-day traffic stays local
