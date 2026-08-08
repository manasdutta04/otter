# Changelog

## 0.2.0 — Engineer core (2026-08-08)

Production release of the shared engineer loop across Docker Web/API, CLI, and docs.

### Docker / Web / API
- New `packages/agent` core: context builder, model budgets, task decomposition, state machine, targeted edits
- Coding generate path uses engineer prepare → implement, intelligence-aware context, and edit-first patches
- Planner → Coding: **Use this plan in Coding** always available (not only when risks exist)
- Platform image `PYTHONPATH` includes `/app` so `packages.agent` imports work in Hub/self-host images
- Contributor `compose.dev.yml` overrides host `.env` DB/Redis/LLM URLs for container DNS
- API version `0.3.0`

### CLI (`@otter-engg/cli` **0.2.0**)
- `/create`: plan → approve → implement → validate (edit-preferring tools)
- Same product contract: understand → plan → approve → build

### Intelligence
- Repository intelligence still powers chat/plan/analyze; agent context builder consumes it on generate

### Docs / site
- Release notes at `/docs/changelog`
- Install surfaces (Docker Hub image + npm CLI) documented for 0.2.0

## 0.1.x

Initial public Docker image (`manasdutta04/otter`) and npm CLI (`@otter-engg/cli`).
