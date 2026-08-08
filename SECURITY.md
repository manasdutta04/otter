# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest `main` | Yes |
| Published `@otter-engg/cli` on npm | Yes (latest) |
| Docker image `manasdutta04/otter:latest` | Yes |

Older tags / releases may not receive security fixes.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

Email the maintainer via the address on the [GitHub profile](https://github.com/manasdutta04), or use [GitHub private vulnerability reporting](https://github.com/manasdutta04/otter/security/advisories/new) if enabled.

Include:

- Description of the issue and impact
- Steps to reproduce or a proof of concept
- Affected surface (Docker image, CLI, API, auth broker, site)
- Whether the issue is already public elsewhere

We aim to acknowledge reports within a few days and will coordinate a fix and disclosure timeline with you.

## Scope notes

- **In scope:** RCE, auth bypass, secret leakage from the published image/CLI, broker misuse that exposes GitHub App secrets, path traversal in repo tooling
- **Out of scope (usually):** Issues that require a malicious local model, physical access to an already-compromised machine, or social engineering of end users

## Hardening tips for operators

- Keep `OTTER_AUTH_BROKER_URL` pointed at your controlled Worker; never bake GitHub Client Secrets into the Docker image or public compose defaults
- Never publish `OTTER_AUTH_REDEEM_SECRET` / `REDEEM_HMAC_SECRET` in git, Docker Hub labels, or public compose files — set them only as Cloudflare secrets / private `.env`
- Treat local Postgres/Redis volumes as sensitive (they hold project data)
- Prefer least privilege when installing the Otter GitHub App on orgs
- Rotate secrets immediately if they ever appear in a public commit or compose default
