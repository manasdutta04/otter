import { GITHUB_REPO } from "../../../lib/urls";

export default function CliDocsPage() {
  return (
    <>
      <h1>CLI</h1>
      <p className="lead">
        The CLI is a thin client of the same Otter API the Docker web UI uses. It does not embed
        Postgres — start Docker first, then log in.
      </p>

      <h2>Prerequisites</h2>
      <ol>
        <li>
          Run the platform stack (<a href="/docs/self-host">Self-host</a>) so{" "}
          <code>http://127.0.0.1:8000</code> is up.
        </li>
        <li>
          Build or install the CLI from <code>apps/cli</code>.
        </li>
      </ol>

      <h2>Login</h2>
      <pre>
        <code>{`otter login
# Browser → Otter GitHub App (Cloudflare broker) → ~/.otter/config.json`}</code>
      </pre>
      <p>
        Same Connect flow as the web UI. See <a href="/docs/github">GitHub</a>.
      </p>

      <h2>Useful commands</h2>
      <ul>
        <li>
          <code>otter repos list</code> / <code>otter repos import &lt;url&gt;</code>
        </li>
        <li>
          <code>otter chat</code> / <code>otter plan</code> / <code>otter review</code>
        </li>
        <li>
          <code>otter logout</code>
        </li>
      </ul>

      <h2>MCP</h2>
      <p>
        After <code>otter login</code>, point your MCP client at{" "}
        <code>python apps/mcp/server.py</code> with <code>OTTER_API_URL=http://127.0.0.1:8000</code>.
        The server reads <code>~/.otter/config.json</code> when <code>OTTER_SESSION</code> is unset.
      </p>

      <h2>Source</h2>
      <p>
        <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
          Repository
        </a>
      </p>
    </>
  );
}
