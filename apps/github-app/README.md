# Otter GitHub App 🦦

Webhook boundary for GitHub App events.

- Verifies `X-Hub-Signature-256` when `GITHUB_WEBHOOK_SECRET` is set
- Accepts `pull_request`, `push`, `installation`, and `ping`
- Forwards durable events to `OTTER_API_URL/internal/github-events` when reachable

```bash
export GITHUB_WEBHOOK_SECRET=...
export OTTER_API_URL=http://api:8000
uvicorn app:app --host 0.0.0.0 --port 9000
```
