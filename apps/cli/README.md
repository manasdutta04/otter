# Otter CLI (`@otter-engg/cli`)

Interactive engineering-intelligence session for your terminal. Part of the public [Otter](https://github.com/manasdutta04/otter) monorepo.

**Docs:** https://otter.manasdutta.com/docs/cli · **npm:** https://www.npmjs.com/package/@otter-engg/cli

## Install

```bash
npm i -g @otter-engg/cli
# pnpm add -g @otter-engg/cli
# yarn global add @otter-engg/cli
# bun add -g @otter-engg/cli
```

## Run

```bash
otter
```

```
otter › explain the auth flow
otter › /scan
otter › /import owner/repo
otter › /create add a health endpoint --pr
otter › /exit
```

Data: `~/.otter/` (config, SQLite, clones).

## Develop

```bash
cd apps/cli
npm install && npm run build
node dist/cli.js
```

See root [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Publish (CI)

GitHub Actions publishes `@otter-engg/cli` via **npm Trusted Publisher (OIDC)** — no `NPM_TOKEN`.

**One-time npm setup:** package → Settings → Trusted Publisher → GitHub Actions:

| Field | Value |
|-------|--------|
| Organization or user | `manasdutta04` |
| Repository | `otter` |
| Workflow filename | `cli-publish.yml` |
| Allowed actions | `npm publish` |

Optional: Publishing access → **Require 2FA and disallow tokens** (OIDC still works).

```bash
# 1) Bump version in apps/cli/package.json
# 2) Push to main → publishes that version (skips if already on npm)
git add apps/cli
git commit -m "release(cli): 0.2.0"
git push origin main


```

Manual: Actions → **Publish @otter-engg/cli** → Run workflow.
