import Link from "next/link";
import { GITHUB_REPO } from "../../../lib/urls";

export default function McpDocsPage() {
  return (
    <>
      <h1>MCP</h1>
      <p className="lead">
        Otter MCP is a stdio Model Context Protocol server: a repository brain for Cursor, Claude
        Desktop, and Claude Code. Impact analysis, architecture guard, verification, and
        approval-gated tasks — not a thin REST proxy.
      </p>

      <h2>Install</h2>
      <pre>
        <code>{`pip install otter-mcp
# or run ephemerally:
uvx otter-mcp`}</code>
      </pre>
      <p>
        No monorepo clone required. Bind a repo with <code>OTTER_REPO_ROOT</code> (or{" "}
        <code>OTTER_REPOSITORY_ID</code> under the API data directory). Optional persistence needs a
        running API plus <code>OTTER_API_URL</code> and <code>OTTER_SESSION</code> (Web/Docker{" "}
        <code>otter_session</code> cookie). CLI GitHub login alone is not an API session.
      </p>

      <h2>Cursor / Claude</h2>
      <pre>
        <code>{`{
  "mcpServers": {
    "otter": {
      "command": "uvx",
      "args": ["otter-mcp"],
      "env": {
        "OTTER_REPO_ROOT": "\${workspaceFolder}"
      }
    }
  }
}`}</code>
      </pre>
      <p>
        Or use <code>&quot;command&quot;: &quot;otter-mcp&quot;</code> after{" "}
        <code>pip install otter-mcp</code>. Logs stay on stderr — stdio is the MCP framing channel.
      </p>

      <h2>What you get</h2>
      <ul>
        <li>
          Deterministic graph impact (<code>otter_impact</code>, <code>otter_dependency_impact</code>
          , <code>otter_change_radar</code>)
        </li>
        <li>
          Evidence-backed constitution + <code>otter_guard</code> / <code>otter_why</code>
        </li>
        <li>
          Allowlisted verify + review gate (<code>PASS</code> / <code>REVIEW</code> /{" "}
          <code>BLOCKED</code>)
        </li>
        <li>
          Task orchestration mapped to Otter code-tasks — apply only after approval
        </li>
      </ul>

      <h2>Approval &amp; security</h2>
      <ul>
        <li>
          <code>otter_task_execute</code> with <code>apply</code> returns{" "}
          <code>approval_required</code> until the code-task is approved — no silent writes
        </li>
        <li>No arbitrary shell tool; runners are allowlisted (npm scripts, pytest, ruff)</li>
        <li>Path traversal on repository ids and relative paths is rejected</li>
      </ul>

      <h2>Source &amp; registry</h2>
      <ul>
        <li>
          PyPI: <code>otter-mcp</code>
        </li>
        <li>
          MCP name: <code>io.github.manasdutta04/otter</code>
        </li>
        <li>
          Source:{" "}
          <a href={`${GITHUB_REPO}/tree/main/apps/mcp`} target="_blank" rel="noreferrer">
            apps/mcp
          </a>
        </li>
      </ul>

      <h2>Related</h2>
      <ul>
        <li>
          <Link href="/docs/cli">CLI</Link>
        </li>
        <li>
          <Link href="/docs/docker">Docker</Link>
        </li>
        <li>
          <Link href="/docs/first-run">First 10 minutes</Link>
        </li>
      </ul>
    </>
  );
}
