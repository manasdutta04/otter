# Otter CLI (`otter-engg`)

Interactive engineering-intelligence session — Claude Code–style terminal UX.

## Install

```bash
npm install -g otter-engg
# or
bun add -g otter-engg
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
