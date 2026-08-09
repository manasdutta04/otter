# Otter MCP — Engineering Intelligence Layer

<!-- mcp-name: io.github.manasdutta04/otter -->

Official [Model Context Protocol](https://modelcontextprotocol.io/) **stdio** server. External AI agents (Cursor, Claude Desktop, Claude Code) get a repository brain: impact, architecture guard, verification, and approval-gated tasks.

## Install (no monorepo clone)

```bash
pip install otter-mcp
# or: uv pip install otter-mcp
```

Or run without a permanent install:

```bash
uvx otter-mcp
```

## Cursor / Claude (`mcp.json`)

```json
{
  "mcpServers": {
    "otter": {
      "command": "uvx",
      "args": ["otter-mcp"],
      "env": {
        "OTTER_REPO_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

If you prefer pip’s console script:

```json
{
  "mcpServers": {
    "otter": {
      "command": "otter-mcp",
      "env": {
        "OTTER_REPO_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

### Optional API persistence

```json
{
  "env": {
    "OTTER_REPO_ROOT": "${workspaceFolder}",
    "OTTER_API_URL": "http://127.0.0.1:8000",
    "OTTER_SESSION": "your-web-otter-session-cookie",
    "OTTER_REPOSITORY_ID": "imported-repo-id"
  }
}
```

**Auth note:** CLI `otter login` (GitHub) is **not** an API session. Export the Web/Docker `otter_session` cookie as `OTTER_SESSION`.

## Requirements

- Python 3.11+
- A local checkout via `OTTER_REPO_ROOT` **and/or** an imported repo under `REPOSITORY_DATA_DIR/{repository_id}`
- Optional: running Otter API for memory / code-tasks

## Tools

| Tool | Purpose |
|------|---------|
| `otter_understand` | Targeted context (retrieval + neighbors) |
| `otter_impact` | Blast radius from a focus path |
| `otter_change_radar` | Pre-write scope / risk / complexity |
| `otter_dependency_impact` | Reverse consumers of a file/module/dep |
| `otter_guard` | Proposal vs inferred constitution |
| `otter_why` | Evidence-backed “why does this exist?” |
| `otter_memory` | List/add memory via API |
| `otter_verify` | Allowlisted tests/lint + architecture |
| `otter_review_gate` | PASS / REVIEW / BLOCKED |
| `otter_task_create` | Plan + optional API code-task (no writes) |
| `otter_task_status` | Task status from API |
| `otter_task_validate` | Review gate vs objective |
| `otter_task_execute` | `generate` / `approve` / `apply` — apply only when approved |

Writes never apply silently: `otter_task_execute` with `apply` returns `approval_required` until status is `approved`.

## Resources & prompts

- Resources: `otter://repo/overview`, `architecture`, `constitution`, `health`, `dependencies`, `otter://task/{id}`…
- Prompts: `otter-investigate`, `otter-plan`, `otter-review`, `otter-debug`, `otter-security-review`, `otter-architecture-review`

## Developer install (from this monorepo)

```bash
pip install -e apps/mcp
export OTTER_REPO_ROOT=/path/to/repo
otter-mcp
```

## Security

- No general `execute_shell` tool — only allowlisted npm scripts / pytest / ruff
- Path traversal rejected on `repository_id` and relative paths
- Oversized tool JSON is truncated in responses

## MCP Registry

Package metadata: [`server.json`](./server.json). Registry name: `io.github.manasdutta04/otter`.

See also: https://otter.manasdutta.com/docs/mcp
