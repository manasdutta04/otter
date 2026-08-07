import { GITHUB_REPO } from "../../../lib/urls";

export default function CliDocsPage() {
  return (
    <>
      <h1>CLI</h1>
      <p className="lead">
        The CLI is a thin client of the same Otter API the Docker web UI uses. It is not a separate
        product brain.
      </p>

      <h2>Status</h2>
      <p>
        Packages live under <code>apps/cli</code> and <code>apps/cli-py</code>. The intended install
        path is something like <code>npx otter</code> / <code>bunx otter</code> against your local
        API — this surface is still being productized.
      </p>

      <h2>Today</h2>
      <ul>
        <li>Self-host the platform with Docker and use the web UI at <code>/app</code>.</li>
        <li>
          Experimental MCP entry: <code>python apps/mcp/server.py</code> with{" "}
          <code>OTTER_API_URL</code> / <code>OTTER_SESSION</code>.
        </li>
      </ul>

      <h2>Source</h2>
      <p>
        Track progress in the{" "}
        <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
          repository
        </a>
        .
      </p>
    </>
  );
}
