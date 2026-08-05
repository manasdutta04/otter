# Architecture Guide

## High-level flow

Web Dashboard, CLI, VS Code Extension, and GitHub App clients communicate with the veridexs API. The API delegates work to the LangGraph agent orchestration layer, which coordinates repository intelligence, retrieval, planning, coding, review, and health analysis.

## Core infrastructure

- PostgreSQL stores application and project metadata.
- Redis and Celery support queues and background repository processing.
- Qdrant stores vector embeddings for repository retrieval and memory.
- GitHub integration provides repository and pull-request context.
- Model access is routed through LiteLLM where practical.

## Boundaries

- `apps/` contains deployable product surfaces.
- `packages/` contains reusable domain and infrastructure capabilities.
- `docs/` contains user and system documentation.
- `docker/` contains local and deployment container assets.

