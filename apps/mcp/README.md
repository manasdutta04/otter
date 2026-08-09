# Otter MCP — Engineering Intelligence Layer

Official [Model Context Protocol](https://modelcontextprotocol.io/) **stdio** server. External AI agents (Cursor, Claude Desktop, Claude Code) get a repository brain: impact, architecture guard, verification, and approval-gated tasks — without wrapping every REST route.

Core analysis lives in `packages/impact`, `packages/architecture`, and `packages/verify`. Persistence (memory, code-tasks) uses the Otter API when `OTTER_SESSION` is set.

## Requirements

- Python 3.11+
- A local checkout (`OTTER_REPO_ROOT`) **and/or** an imported repo under `REPOSITORY_DATA_DIR/{repository_id}`
- Optional: running Otter API + Web session for memory / code-tasks

**Auth note:** CLI `otter login` (GitHub) is **not** an API session. For HTTP tools, export the Web/Docker `otter_session` cookie as `OTTER_SESSION`.

## Install

From the monorepo root:

```bash
pip install -e apps/mcp
# or
pip install "mcp>=1.6" httpx
```

## Run

```bash
export OTTER_REPO_ROOT=/path/to/your/repo   # local Cursor workspace
# optional persistence:
export OTTER_API_URL=http://127.0.0.1:8000
export OTTER_SESSION=...                    # Web cookie / x-otter-session
export OTTER_REPOSITORY_ID=...              # for API-backed tools/resources

otter-mcp
# or: python -m otter_mcp
# or: python apps/mcp/server.py
```

## Cursor (`mcp.json`)

```json
{
  "mcpServers": {
    "otter": {
      "command": "python",
      "args": ["-m", "otter_mcp"],
      "cwd": "C:/Coding Workspace/veridexs/apps/mcp",
      "env": {
        "PYTHONPATH": "C:/Coding Workspace/veridexs;C:/Coding Workspace/veridexs/apps/mcp",
        "OTTER_REPO_ROOT": "C:/path/to/active/workspace",
        "OTTER_API_URL": "http://127.0.0.1:8000",
        "OTTER_SESSION": ""
      }
    }
  }
}
```

## Claude Desktop

Add under `mcpServers` in the Claude Desktop config:

```json
{
  "mcpServers": {
    "otter": {
      "command": "python",
      "args": ["-m", "otter_mcp"],
      "cwd": "/absolute/path/to/veridexs/apps/mcp",
      "env": {
        "PYTHONPATH": "/absolute/path/to/veridexs:/absolute/path/to/veridexs/apps/mcp",
        "OTTER_REPO_ROOT": "/absolute/path/to/repo"
      }
    }
  }
}
```

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

## Resources

- `otter://repo/overview`, `architecture`, `constitution`, `health`, `dependencies`
- `otter://task/{id}`, `.../plan`, `.../diff`, `.../verification` (API session + `OTTER_REPOSITORY_ID`)

## Prompts

`otter-investigate`, `otter-plan`, `otter-review`, `otter-debug`, `otter-security-review`, `otter-architecture-review`

## Security

- No general `execute_shell` tool — only allowlisted npm scripts / pytest / ruff
- Path traversal rejected on `repository_id` and relative paths
- Oversized tool JSON is truncated in responses

## Tests

```bash
cd apps/mcp
PYTHONPATH=../..:. pytest tests -q
```

See also site docs: `/docs/mcp`.
