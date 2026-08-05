# veridexs Agent Guide

veridexs is an engineering-intelligence platform that understands repositories, explains architecture, plans changes, assists with coding, and reviews engineering quality.

## Working principles

- Understand the repository before proposing or applying changes.
- Explain before coding and show the affected files.
- Preserve project conventions and avoid silent overwrites.
- Require human approval before applying generated code changes.
- Prefer small, verifiable changes with tests where applicable.
- Treat repository context, conversations, and engineering decisions as project memory.

## Scope

The product is organized into applications under `apps/` and reusable capabilities under `packages/`. Product requirements are defined in `PRD.md`.

