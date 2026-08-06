# Otter CLI 🦦

Thin TypeScript client for the Otter API. Same contract as the web workspace.

## Install / run

```bash
# from repo
cd apps/cli && npm install && npm run build
node dist/cli.js --help

# published / one-shot (after npm publish)
npx otter login
bunx otter repos list
```

## Auth

`otter login` opens GitHub OAuth and writes `~/.otter/config.json`.

You can also set `OTTER_SESSION` and `OTTER_API_URL`.

## Commands

- `login` / `logout`
- `health`
- `repos list|import|status`
- `analyze` / `chat` / `plan` / `health-report` / `review` / `architect` / `docs`

Legacy Python client lives in `apps/cli-py` for internal use only.
