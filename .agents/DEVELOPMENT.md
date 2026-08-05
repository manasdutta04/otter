# Development Guide

## Development sequence

1. Read the relevant product requirement and existing package boundaries.
2. Inspect repository context before changing code.
3. Plan the change and identify affected applications and packages.
4. Implement the smallest coherent change.
5. Add or update tests and documentation.
6. Run formatting, linting, type checks, and tests for the affected areas.

## Engineering expectations

- Keep domain logic reusable and avoid coupling it to a single client.
- Make background work observable and retry-safe.
- Keep model-provider integrations replaceable.
- Never expose secrets, tokens, prompts containing private data, or repository contents in logs.
- Make destructive or code-writing actions explicit and approval-gated.

## Implementation learning log

Every implementation step must be explained alongside the code. Append the intent, request flow, data flow, rationale, validation, and known limitations to `.agents/IMPLEMENTATION_LOG.md`. The explanation should teach the system boundary and trade-offs in plain language, not merely list changed files.
