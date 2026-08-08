# Otter MCP bridge

Stdio JSON-RPC bridge to a running Otter API (usually the Docker stack on `:8000`).

## Run

```bash
export OTTER_API_URL=http://127.0.0.1:8000
export OTTER_SESSION=your_session_token   # or rely on ~/.otter/config.json after `otter login`
python apps/mcp/server.py
```

## Tools

`repository_intelligence`, `repository_chat`, `repository_plan`, `repository_review`, `repository_health`, `repository_memory`.

Same product contract as the Otter web app and CLI. See the [main README](../../README.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md).
