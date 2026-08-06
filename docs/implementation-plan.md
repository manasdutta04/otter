# veridexs Implementation Plan

This document turns the current product direction into a phased execution plan. The goal is not to polish the existing demo into a larger demo. The goal is to make veridexs production-ready as an engineering-intelligence platform that a real team can trust.

## Product goals

veridexs should:

- Understand repositories deeply.
- Explain architecture clearly.
- Plan changes before code is written.
- Generate code only with review and approval.
- Review quality, security, and performance.
- Remember engineering decisions over time.
- Expose the same core capabilities through the web app, CLI, VS Code extension, GitHub App, and MCP server.

## Current problems to fix first

These are the issues visible in the current repo and dashboard experience:

- The web app is effectively a single-page workspace instead of a product with clear navigation and distinct work areas.
- Repository import status stays stale until a full browser refresh instead of updating the UI automatically.
- Several lower-level product actions are present in the UI but are not yet fully wired or reliable.
- Some repository intelligence and “below-the-fold” experiences feel like placeholders rather than finished product surfaces.
- The system needs stronger production discipline around tests, job reliability, observability, and integration boundaries.

## Guiding principles

- Stabilize the core workflow before adding more features.
- Prefer durable state and clear contracts over in-memory shortcuts.
- Keep AI provider integration behind a small abstraction so models can be swapped without rewriting product logic.
- Make background work observable and retry-safe.
- Require explicit approval before any code-writing action.
- Use one shared backend contract across all clients.
- Ship features only when they are backed by tests and visible product value.

## Phase 0. Stabilize the baseline

### Goal
Make the current product reliable enough that the existing dashboard, import flow, and repository intelligence loop can be trusted.

### Work items

- Fix stale repository status updates in the UI with polling, server-sent events, or websocket-based refresh.
- Split the dashboard into real routes and sections instead of one long page.
- Audit every existing button, card, and lower-level action in the dashboard and either wire it properly or hide it until it works.
- Add robust loading, empty, success, and failure states for repository import and analysis.
- Verify the import worker, API, and database models all agree on the same job state transitions.
- Add focused tests for job lifecycle, repository status refresh, and error handling.
- Remove any feature placeholders that are exposed as finished functionality.

### Exit criteria

- Repository status changes appear in the UI without manual refresh.
- No visible action in the dashboard is dead or misleading.
- Import success and failure are obvious to the user.
- The current slice has tests covering the critical path.

## Phase 1. Rebuild the web experience into a real product shell

### Goal
Replace the single-page feel with a structured product that has clear information architecture.

### Work items

- Create a landing experience and authenticated workspace experience with different routes.
- Add a repository list view, repository detail view, intelligence view, chat view, planning view, health view, and settings view.
- Introduce shared navigation, header, breadcrumbs, and status indicators.
- Add reusable UI components for cards, panels, timelines, badges, file lists, and empty states.
- Make the dashboard responsive and usable on desktop and smaller screens.
- Make the design feel intentional and product-like, not like a thin internal tool.

### Exit criteria

- Users can move between distinct product areas.
- The current dashboard no longer feels like one unfinished page.
- The repository workspace has obvious entry points for intelligence, chat, planning, and health.

## Phase 2. Harden the repository intelligence core

### Goal
Make repository import, analysis, and search the durable foundation of the platform.

### Work items

- Keep repository import job state in PostgreSQL as the source of truth.
- Make import, analysis, and indexing fully asynchronous and retry-safe.
- Persist repository summaries, folders, entry points, architecture signals, and graph data.
- Expand the analyzer so it produces grounded, useful signals rather than shallow heuristics.
- Add repository chat that can cite source files and explain why it answered the way it did.
- Introduce retrieval infrastructure for repository memory and code lookup.
- Add deterministic fallbacks when LLM calls are unavailable.

### Exit criteria

- Imported repositories consistently move through queued, cloning, analyzing, and ready states.
- Intelligence results are persisted, queryable, and reproducible.
- Chat answers are grounded in repository data, not generic model output.

## Phase 3. Add engineering memory and planning

### Goal
Turn veridexs into a tool that remembers the project and can plan work before code is written.

### Work items

- Persist engineering memory for decisions, conventions, architecture notes, and recurring instructions.
- Add a planner that can produce scoped implementation plans from a user request.
- Generate affected files, dependencies, risks, and verification steps for each plan.
- Support plan versioning and plan history.
- Tie planning outputs to the selected repository context.
- Make plans readable enough for a human to approve or reject confidently.

### Exit criteria

- A user can ask for a change and get a structured, repository-aware plan.
- The system remembers prior decisions and can reuse them instead of repeating the same explanations.

## Phase 4. Add safe AI coding workflows

### Goal
Allow code generation, patching, and review without losing human control.

### Work items

- Build a code task workflow that separates request, proposal, approval, and application.
- Generate patches only after a user approves the proposed change.
- Show diffs and affected files clearly before any write action.
- Add test generation alongside code edits where appropriate.
- Add safety checks for path traversal, unsafe write targets, and malformed patch content.
- Track task state so users can resume work later.

### Exit criteria

- No code is changed without explicit approval.
- Generated patches are visible and reviewable.
- Applied tasks leave a durable audit trail.

## Phase 5. Expand review and health analysis

### Goal
Make veridexs useful as a senior-engineer review assistant, not just a repository browser.

### Work items

- Add repository health scoring that is meaningful and explainable.
- Improve architecture analysis, performance analysis, dependency analysis, and code review signals.
- Surface issues with severity, rationale, and file references.
- Detect missing tests, dead code, duplication, and suspicious patterns.
- Add dashboards for quality trends over time.
- Make review output actionable rather than generic.

### Exit criteria

- Each repository has a clear health profile with understandable scores.
- Reviews identify concrete issues and point to the relevant code.
- Quality trends are visible across time, not just at import time.

## Phase 6. Ship the companion surfaces

### Goal
Expose the same engine through the other product surfaces from the PRD.

### Work items

- Build the CLI around the same backend contract as the web app.
- Expand the VS Code extension with explain, review, plan, architect, and fix commands.
- Harden the GitHub App so it can comment on pull requests and repository events.
- Stabilize the MCP server so external tools can query veridexs consistently.
- Keep all companion surfaces thin and opinionated, not duplicate implementations.

### Exit criteria

- The CLI, VS Code extension, GitHub App, and MCP server all rely on the same backend capabilities.
- No surface contains separate business logic that drifts from the main API.

## Phase 7. Production readiness

### Goal
Make the system safe to run for real teams.

### Work items

- Add proper database migrations for every schema change.
- Improve authentication, session handling, and token storage security.
- Add observability: structured logs, metrics, tracing, and job monitoring.
- Add CI checks for tests, linting, type checking, and build validation.
- Add deployment and rollback guidance.
- Add integration tests for the end-to-end repository workflow.
- Document local development, production configuration, and operational recovery steps.

### Exit criteria

- The platform can be deployed and maintained with predictable behavior.
- A failed job, failed analysis, or failed UI refresh can be debugged quickly.
- Security and reliability are explicit parts of the release process.

## Recommended execution order

1. Stabilize the import/status flow and remove the misleading UI states.
2. Rebuild the web shell into distinct pages and views.
3. Harden repository intelligence, chat, and persistence.
4. Add memory and planning.
5. Add safe coding workflows.
6. Expand review and health analysis.
7. Ship the CLI, VS Code, GitHub App, and MCP surfaces.
8. Finish production hardening.

## Definition of done

veridexs is in good shape when a developer can:

- Connect GitHub.
- Import a repository.
- See repository state update live.
- Understand the architecture from the dashboard.
- Ask grounded questions about the codebase.
- Generate a safe plan for a change.
- Review code quality and health.
- Use the same intelligence through web, CLI, VS Code, GitHub, and MCP.

That is the product described by the PRD, and that is the bar this repository should meet.
