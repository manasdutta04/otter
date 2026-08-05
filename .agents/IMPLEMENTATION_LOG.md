# veridexs Implementation Log

This document explains what has been implemented so far and why. It is written as a learning guide alongside the code. Each future implementation step should append a new dated section before or after the code change.

## Product direction

veridexs is being built as an engineering-intelligence platform, not as a single-page AI demo. The long-term product must understand repositories, explain architecture, retain engineering memory, plan changes, assist with coding, review pull requests, and analyze repository health.

The current work is the first infrastructure-backed vertical slice of that platform. It establishes real application boundaries and a real authenticated repository workflow so later intelligence features have a durable foundation.

## Step 1 — Repository scaffold

### What was created

The repository was organized into the PRD’s intended boundaries:

- `apps/web` — Next.js dashboard.
- `apps/api` — FastAPI backend.
- `apps/cli`, `apps/vscode`, `apps/github-app` — future client and integration surfaces.
- `packages/*` — future reusable agent, planner, analyzer, memory, retrieval, architecture, review, health, and shared capabilities.
- `docs`, `examples`, and `docker` — documentation, examples, and runtime assets.

The `.agents` directory received project guides for architecture, development, deployment, contribution rules, and agent behavior.

### Why

The folder boundaries reflect the product architecture before feature code is added. This prevents the first feature from becoming a tightly coupled application that is difficult to expand into CLI, VS Code, GitHub App, and agent packages later.

## Step 2 — Local monorepo runtime

### What was implemented

The root package scripts and Docker Compose runtime were added. The local stack contains:

- Next.js web application on port `3000`.
- FastAPI API on port `8000`.
- PostgreSQL on port `5432`.
- Redis on port `6379`.

The API image installs the `git` executable because GitPython is a Python wrapper around the Git command-line tool. The web and API each have their own Dockerfile.

### Why

Repository intelligence requires more than a frontend process. PostgreSQL is the source of durable application state, Redis is reserved for background work, and the API container needs Git to clone repositories. Compose makes the complete local system reproducible.

## Step 3 — GitHub authentication

### Request flow

1. The dashboard links to `GET /auth/github/login`.
2. The API redirects the user to GitHub’s OAuth authorization page.
3. GitHub redirects to `GET /auth/github/callback` with a temporary authorization code.
4. The API exchanges that code for a GitHub access token.
5. The API fetches the GitHub user profile.
6. The API creates or updates the local user and creates an application session.
7. The browser receives only an opaque HttpOnly session cookie and is redirected to the dashboard.

The GitHub access token is never returned in the browser response.

### Why

The browser should not receive or render provider credentials. The application needs a session abstraction so GitHub can eventually be joined by other identity providers and so authorization can be enforced by veridexs rather than by frontend state.

## Step 4 — PostgreSQL persistence

### What is stored

The API now initializes three PostgreSQL tables at startup:

- `users` — local user identity linked to a GitHub account.
- `auth_sessions` — opaque session ID, user ownership, GitHub token, and expiry.
- `repositories` — imported repository URL, owner, status, branch, file count, and errors.

SQLAlchemy’s async engine and `asyncpg` connect the FastAPI service to PostgreSQL.

### Why

The first version stored sessions and repositories in process memory. That meant a restart erased state and multiple API workers could not share it. PostgreSQL makes users, sessions, and imports survive restarts and provides the ownership boundary needed for a multi-user product.

## Step 5 — Authenticated repository import

### Request flow

1. The dashboard checks `GET /auth/me` with credentials included.
2. Protected repository endpoints validate the HttpOnly session cookie.
3. The API verifies the session belongs to a non-expired persisted session.
4. `POST /repositories` accepts a GitHub URL.
5. The API creates a persisted repository record with `queued` status.
6. A background task performs a shallow clone using the server-held GitHub token.
7. The record changes to `cloning`, then `ready` or `failed`.
8. The dashboard displays the repository status, branch, and file count.

The token is used only by the API during cloning and is not placed in the repository record or returned by the API response.

### Why

The authenticated import is the first real product loop: a user connects an identity, imports a codebase, and sees durable workspace state. Later indexing, parsing, embeddings, architecture graphs, and chat can consume the cloned repository records.

## Step 6 — Dashboard

The dashboard is intentionally a workspace entry point rather than a generic chat screen. It provides:

- GitHub connection state.
- Repository URL import.
- Empty workspace state.
- Repository cards.
- Import status feedback.
- Responsive layout.

The visual direction uses an editorial engineering workspace: warm paper tones, dark ink, orange action accents, mono labels, and a display serif for emphasis. This gives the product a distinct identity while keeping the first workflow readable.

## Configuration

Copy `.env.example` to `.env` in the repository root. The Compose file explicitly loads this root file because the Compose file itself lives under `docker/`.

Required local values:

```env
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_URL=http://localhost:3000
DATABASE_URL=postgresql+asyncpg://veridexs:veridexs@postgres:5432/veridexs
REDIS_URL=redis://redis:6379/0
REPOSITORY_DATA_DIR=/data/repositories
```

`.env` is ignored by Git and must never be committed.

## Validation performed

- Python API modules compile successfully.
- Docker Compose configuration validates.
- PostgreSQL, Redis, API, and web containers start successfully.
- API health returns `{"status":"ok","service":"api"}`.
- Web application returns HTTP `200`.
- Unauthenticated repository access returns HTTP `401`.
- GitHub environment variables were verified inside the API container without printing their values.

## Commits delivered

- `cf014d7` — Build phase one repository intelligence slice.
- `12aefee` — Install Git in API runtime image.
- `342d264` — Load root environment in Docker Compose.
- `c4296d8` — Secure GitHub OAuth callback session.
- `64ab212` — Connect authenticated sessions to repository imports.
- `eeb45d6` — Persist users, sessions, and repositories.

All commits were pushed to `origin/main`.

## Current limitations

These are deliberate next-stage items, not hidden assumptions:

- Table creation currently happens at startup; Alembic migrations are needed before production.
- Repository cloning uses an in-process task; Celery/Redis workers should own durable import jobs.
- GitHub tokens are stored in the session table and should be encrypted at rest.
- There is no logout endpoint yet.
- Session cookies need production `Secure` behavior and stronger CSRF protections.
- Repository data is currently scoped by user, but repository records need stronger URL normalization and duplicate handling.
- The repository is cloned, but indexing, Tree-sitter analysis, embeddings, architecture graphs, and repository chat are not implemented yet.
- Automated API and frontend tests need to be added before expanding the feature surface.

## Next implementation boundary

The next safe platform step is to introduce Alembic migrations and a durable Redis/Celery import worker. That will make schema changes explicit and prevent repository imports from being lost when an API process restarts.

## Step 7 — Durable repository import infrastructure

### What changed

The recommended platform step was implemented:

- Alembic now owns database schema versioning.
- The initial migration creates the existing user, session, and repository tables safely with `IF NOT EXISTS`, preserving the current local PostgreSQL volume.
- The API no longer creates tables during application startup.
- `repository_import_jobs` stores each import attempt and its lifecycle.
- Celery uses Redis as its broker and result backend.
- A dedicated worker owns Git cloning and repository inspection.
- Docker Compose now starts a one-shot migration service and an independently scalable worker service.

### New import flow

`POST /repositories` now writes the repository and a queued import job, publishes only the repository ID and job ID to Celery, and returns immediately. The worker loads the job and repository from PostgreSQL, obtains the user’s active server-side GitHub token, clones the repository, records the branch and file count, and persists either success or a sanitized failure.

The token is deliberately not included in the Celery message. Worker failures are retried up to three times with exponential backoff, and the final failure is recorded in both the job and repository records.

### New API endpoints

- `GET /repositories/{repository_id}/import-status` returns the latest durable import job.
- `POST /repositories/{repository_id}/retry-import` creates a new job for the repository owner.
- `POST /auth/logout` removes the persisted session and clears the browser cookie.

### Runtime validation

- Alembic migration completed successfully against the existing PostgreSQL volume.
- API, web, PostgreSQL, Redis, migration, and worker services started through Compose.
- Celery worker connected to `redis://redis:6379/0` and registered `repositories.import`.
- API health returned successfully.
- Three backend tests passed, including secret redaction and import lifecycle schema validation.

### Learning notes

The API is now a control plane: it authenticates users, writes intent, and reports state. The worker is the execution plane: it performs slow and failure-prone repository work. PostgreSQL is the source of truth for state, while Redis only transports task messages. This separation allows API and worker processes to restart or scale independently.

The next hardening work is to add integration tests for actual Celery task transitions, encrypt GitHub tokens at rest, and add explicit migration upgrade/downgrade checks in CI.

## Step 8 — Phase 1 completion: repository intelligence and chat

### What changed

The remaining Phase 1 product capabilities were implemented:

- Added repository intelligence persistence.
- Added a deterministic repository analyzer that detects manifests, languages, folders, entry points, README context, and architecture signals.
- The import worker now analyzes a repository after cloning and stores the result before marking the import complete.
- Added `GET /repositories/{repository_id}/intelligence`.
- Added `POST /repositories/{repository_id}/chat`.
- Updated the dashboard so users can select a repository, view its intelligence read, and ask contextual questions.

### How the Phase 1 chat works

The current chat endpoint is intentionally a grounded repository lookup rather than a generic AI response. It uses the imported repository’s file structure and persisted intelligence to answer questions about authentication, architecture, folders, and likely matching files. It returns source file paths with the answer.

This creates a truthful foundation for the later LangGraph/RAG model layer. The system has repository context and source references before a model is introduced.

### Phase 1 is now complete

The Phase 1 PRD loop is covered:

- GitHub authentication.
- GitHub URL repository import.
- Durable PostgreSQL users, sessions, repositories, and import jobs.
- Background repository processing with Redis/Celery.
- Repository summary and structural intelligence.
- Repository contextual chat.
- Basic engineering dashboard.

### Validation

- Alembic upgraded the existing database from `0001_initial` to `0002_intelligence`.
- API, worker, web, Redis, PostgreSQL, and migration services are running.
- API health returned successfully.
- Analyzer tests passed alongside worker and schema tests.

### Explicit boundary

Phase 1 chat is deterministic and source-grounded. LangGraph orchestration, vector embeddings, Qdrant retrieval, multi-model routing, architecture diagrams, and production code generation remain later platform phases. This boundary keeps the first release inspectable and avoids presenting a simple model wrapper as the finished veridexs product.
