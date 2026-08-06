# Otter Deployment Guide

Production topology: web (Next.js), API (FastAPI), Celery worker, PostgreSQL, Redis, Otter GitHub App, and optional Qdrant.

## Requirements

- Containerize deployable services with Docker (`docker/compose.yml` as the local reference).
- Store secrets in the environment (`GITHUB_*`, `LLM_*`, `OTTER_INTERNAL_TOKEN`, DB credentials) — never in source control.
- Run Alembic migrations as an explicit release step (`alembic upgrade head`).
- Scale API and worker independently.
- Persist PostgreSQL (and Qdrant when enabled) on durable volumes.
- Health checks: API `/health`, GitHub App `/health`, web HTTP 200.
- Structured logs and error reporting in production.

## Release safety

Deploy progressively, verify queues and import jobs, and keep a rollback path for each release.

## Surfaces after deploy

- Web: marketing `/`, workspace `/app`
- CLI: `npx otter` against production `OTTER_API_URL`
- MCP: `OTTER_API_URL` + `OTTER_SESSION`
- GitHub App webhooks → `/internal/github-events`
