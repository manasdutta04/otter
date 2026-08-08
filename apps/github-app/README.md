# Otter GitHub App webhook service

Receives GitHub App webhooks and forwards durable events to the Otter API.

## Behavior

- Verifies `X-Hub-Signature-256` when `GITHUB_WEBHOOK_SECRET` is set
- Accepts `pull_request`, `push`, `installation`, and `ping`
- Forwards to `OTTER_API_URL/internal/github-events` when reachable

## Run

```bash
export GITHUB_WEBHOOK_SECRET=...
export OTTER_API_URL=http://127.0.0.1:8000
uvicorn app:app --host 0.0.0.0 --port 9000
```

End-user Connect GitHub flow uses the Cloudflare **auth broker** (`apps/auth-broker`), not this service directly. See https://otter.manasdutta.com/docs/github and [CONTRIBUTING.md](../../CONTRIBUTING.md).
