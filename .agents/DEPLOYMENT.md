# Otter Deployment Guide

Self-host topology (default): **one** `otter/platform` container (API + web + worker) plus official PostgreSQL and Redis. Ollama/LLM stays on the host or a remote OpenAI-compatible endpoint.

## Requirements

- Product install: `docker/compose.platform.yml` (see [docs/self-host.md](../docs/self-host.md)).
- Contributor bind-mounts: `docker/compose.dev.yml`.
- Store secrets in the environment (`GITHUB_*`, `LLM_*`, `OTTER_INTERNAL_TOKEN`, DB credentials) — never in source control.
- Platform image runs `alembic upgrade head` on boot; do not skip migrations.
- Persist PostgreSQL and `repository_data` volumes.
- Health checks: API `/health`, web HTTP 200 on `:3000`.
- Structured logs from supervisord (stdout of api/worker/web).

## Release safety

Deploy progressively, verify import jobs and queues (Redis), and keep a rollback path (previous image tag) for each release.

## Surfaces after deploy

- Web: marketing `/`, workspace `/app`
- CLI: `npx otter` against `OTTER_API_URL` (e.g. `http://127.0.0.1:8000`)
- MCP: `OTTER_API_URL` + `OTTER_SESSION`
- GitHub App: optional (`compose.dev.yml --profile github`)
