import { CopyCommand } from "../../../components/CopyCommand";
import { DOCKER_HUB, DOCKER_IMAGE, DOCKER_QUICKSTART } from "../../../lib/urls";

export default function SelfHostDocsPage() {
  return (
    <>
      <h1>Self-host</h1>
      <p className="lead">
        No GitHub clone required. Pull the public image, start Compose (local Postgres + Redis
        auto-created), then Connect GitHub via the Otter GitHub App.
      </p>

      <h2>Run</h2>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />
      <p className="muted" style={{ marginTop: "0.85rem" }}>
        Or: <code>{DOCKER_QUICKSTART}</code>
      </p>
      <p>
        Then open <code>http://127.0.0.1:3000/app</code>. Image:{" "}
        <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
          <code>{DOCKER_IMAGE}</code>
        </a>
        .
      </p>

      <h2>Requirements</h2>
      <ul>
        <li>Docker Engine + Compose v2</li>
        <li>Ollama on the host (recommended): <code>ollama pull qwen2.5-coder:7b</code></li>
      </ul>

      <h2>Connect GitHub</h2>
      <p>
        Click <strong>Connect GitHub</strong> in the UI (or <code>otter login</code>). You install the
        Otter GitHub App — you do <strong>not</strong> paste Client secrets or create your own OAuth
        app. Details: <a href="/docs/github">GitHub docs</a>.
      </p>

      <h2>CLI and MCP</h2>
      <p>
        Keep Docker running, then use the CLI/MCP against <code>http://127.0.0.1:8000</code>. The CLI
        does not embed a database — it uses the same local API + Postgres as the web UI.
      </p>
      <pre>
        <code>{`otter login
otter repos list

# MCP (after otter login) — example env
# OTTER_API_URL=http://127.0.0.1:8000
# OTTER_SESSION is optional if ~/.otter/config.json exists`}</code>
      </pre>

      <h2>Open the product UI</h2>
      <ul>
        <li>
          Workspace: <code>http://127.0.0.1:3000/app</code>
        </li>
        <li>
          Models: <code>http://127.0.0.1:3000/app/models</code>
        </li>
        <li>
          API: <code>http://127.0.0.1:8000</code>
        </li>
      </ul>

      <h2>First-run checklist</h2>
      <ol>
        <li>Compose up (DB created in Docker).</li>
        <li>Connect GitHub (Otter app).</li>
        <li>Open Models and select Local Ollama.</li>
        <li>Import a repository URL.</li>
      </ol>
    </>
  );
}
