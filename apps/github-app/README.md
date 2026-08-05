# veridexs GitHub App boundary

This service is the webhook boundary for GitHub App events. Configure `GITHUB_WEBHOOK_SECRET` to require GitHub's `X-Hub-Signature-256`; without it, local development accepts unsigned events. Event processing will be connected to durable repository jobs in the next GitHub integration hardening step.
