# Package boundaries

Domain packages under `packages/` own shared logic used by the API (and eventually other surfaces).

## Current layout

| Package | Role |
|---------|------|
| `packages/agent` | Engineer core: state machine, context builder, model budgets, decompose/graph, tool permissions, targeted edits, orchestrate (`prepare_engineering_run` → `begin_implement`) |
| `packages/retrieval` | Chat / grounded retrieval |
| `packages/planner` | Plan generation helpers |
| `packages/analyzer`, `review`, `health`, `memory`, `graph`, … | Domain scanners (see each package) |

## Wiring today

- **Docker Web/API:** `apps/api` imports `packages.agent` on code-task generate/apply. Intelligence lives in `apps/api/app/intelligence/` and is passed into the agent context builder.
- **CLI:** TypeScript agent under `apps/cli` mirrors the same stages (plan → approve → implement → validate); it does not import the Python package.
- **MCP:** bridges to the local API.

The Celery worker still uses some `apps/api/app/*` implementations for import-time analysis because several package modules import `app.models` (API-coupled).

Next hardening step: split DB persistence helpers out of `packages/*/repository.py` so scanners stay importable without SQLAlchemy app models.
