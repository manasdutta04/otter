# Otter Implementation Log

This document tracks implementation progression and architectural decisions for Otter.

## Step 12 — Otter Product Rebuild (Web-First) (2026-08-06)

### What was implemented

1. **Rebrand**: Product renamed from veridexs to **Otter** across API cookies (`otter_session`), env vars (`OTTER_*`), Docker DB credentials (`otter`), docs, and UI (🦦).
2. **API wiring**: Fixed planner/memory/docs imports (`save_plan`, `add_memory`, `generate_overview`); CLI OAuth via `cli_port` + local callback; `X-Otter-Session` header; `/internal/github-events` sink; `CodeTaskResponse.from_task` for JSON `changed_files`.
3. **Web product**: Marketing landing at `/` with USP sections; authenticated workspace at `/app`; multi-route repository shell (intelligence, chat, planner, memory, health, review, coding tasks, settings).
4. **TypeScript CLI**: `apps/cli` publishable as `otter` with `npx`/`bunx` bin — login, repos, analyze, chat, plan, review, etc. Legacy Python moved to `apps/cli-py`.
5. **MCP / VS Code / GitHub App**: Expanded MCP tools + initialize; Otter VS Code commands; GitHub App event forwarding to API.
6. **Production baseline**: GitHub Actions CI workflow; deployment guide updated.

## Step 11 — Domain Packages, Grounded Retrieval & Web Shell Expansion (2026-08-06)

### What was implemented

1. Shared domain packages under `packages/` for retrieval, analyzer, planner, memory, review, health.
2. Hybrid TF-IDF/keyword grounded retrieval with line citations.
3. Companion surface alignment for MCP and VS Code.
4. E2E analysis/planner/review test coverage.
