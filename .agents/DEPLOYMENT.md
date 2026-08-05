# Deployment Guide

The planned production topology consists of the web application, API, background worker, PostgreSQL, Redis, Qdrant, Nginx, and external GitHub/model-provider integrations.

## Deployment requirements

- Containerize deployable services with Docker.
- Store secrets in the deployment environment, never in source control.
- Run database migrations as an explicit release step.
- Keep API and worker processes independently scalable.
- Persist PostgreSQL and Qdrant data using managed or durable storage.
- Configure health checks, structured logs, metrics, and error reporting.
- Use GitHub Actions for validation and deployment automation.

## Release safety

Deploy changes progressively, verify health checks and background queues, and provide a rollback path for each release.

