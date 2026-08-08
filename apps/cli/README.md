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

GitHub Actions publishes `@otter-engg/cli` to npm on push.

**Secret:** repo → Settings → Secrets and variables → Actions → `NPM_TOKEN`  
(npmjs.com → Access Tokens → **Automation** token with publish rights to the `otter-engg` org)

```bash
# 1) Bump version in apps/cli/package.json (and lockfile if needed)
# 2) Push to main → publishes that version (skips if already on npm)
git add apps/cli
git commit -m "release(cli): 0.1.2"
git push origin main

# Optional explicit tag release:
git tag cli-v0.1.2
git push origin cli-v0.1.2
```

Manual: Actions → **Publish @otter-engg/cli** → Run workflow.