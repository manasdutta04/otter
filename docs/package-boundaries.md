# Package boundaries

Domain packages under `packages/` should eventually own analyzer, planner, retrieval, review, health, memory, and graph logic.

Today the Celery worker still uses `apps/api/app/*` implementations for import-time analysis because several package modules import `app.models` (API-coupled). The API chat/plan routes already use `packages.retrieval` and `packages.planner`.

Next hardening step: split DB persistence helpers out of `packages/*/repository.py` so scanners stay importable without SQLAlchemy app models.
