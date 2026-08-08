# Otter CLI (`@otter-engg/cli`)

Interactive engineering intelligence for your terminal. Part of [Otter](https://github.com/manasdutta04/otter).

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

Data lives under `~/.otter/`.

## Develop

```bash
cd apps/cli
npm install && npm run build
node dist/cli.js
```

See the root [CONTRIBUTING.md](../../CONTRIBUTING.md).
