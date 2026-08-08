# Otter CLI (`@otter-engg/cli`)

Interactive engineering-intelligence session — Claude Code–style terminal UX.

## Install

```bash
npm install -g @otter-engg/cli
# or
bun add -g @otter-engg/cli
```

## Run

```bash
otter
```

You get a splash, optional GitHub / model setup, then an interactive session:

```
otter › explain the auth flow
otter › /scan
otter › /import owner/repo
otter › /exit
```

Data: `~/.otter/` (config, SQLite, clones).

## Develop

```bash
cd apps/cli
npm install && npm run build
node dist/cli.js
```

## Publish (org `otter-engg`)

```bash
cd apps/cli
npm run build
npm publish --access public
```

Appears under https://www.npmjs.com/settings/otter-engg/packages as `@otter-engg/cli`.
