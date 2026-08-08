# Otter auth broker

Cloudflare Worker that completes **Otter GitHub App** login for the web UI and CLI.

End users never see Client Secrets — they click **Connect GitHub** / run `otter login`, and the broker returns a short-lived one-time code. Seeing the Worker URL in the browser or terminal is normal and safe (it is a public login entrypoint, like any OAuth start URL). Secrets stay in Cloudflare.

## Contributor mode

You usually do **not** need to run this Worker locally. Point `OTTER_AUTH_BROKER_URL` at the public broker (see root `.env.example`).

To fork/deploy your own broker:

```bash
cd apps/auth-broker
npm install
# Edit wrangler.toml — set AUTH_KV ids from `wrangler kv namespace create AUTH_KV`
npx wrangler secret put GITHUB_APP_CLIENT_ID
npx wrangler secret put GITHUB_APP_CLIENT_SECRET
# Optional extra check for API redeem:
# npx wrangler secret put REDEEM_HMAC_SECRET
npm run dev
# npm run deploy
```

Never commit Client Secrets, redeem secrets, or npm tokens. Keep them in Cloudflare Secrets / your private `.env` only.

## Related

- Public docs: https://otter.manasdutta.com/docs/github
- Webhook service: `apps/github-app`
- Platform compose sets `OTTER_AUTH_BROKER_URL` (public URL only — no default redeem secret)

See root [CONTRIBUTING.md](../../CONTRIBUTING.md) and [SECURITY.md](../../SECURITY.md).
