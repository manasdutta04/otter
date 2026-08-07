import { CopyCommand } from "../../../components/CopyCommand";
import { DOCKER_HUB, DOCKER_IMAGE, DOCKER_QUICKSTART } from "../../../lib/urls";

export default function SelfHostDocsPage() {
  return (
    <>
      <h1>Self-host</h1>
      <p className="lead">
        No GitHub clone required. Pull the public image from Docker Hub and start the stack with one
        command. The compose file is hosted on this site.
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

      <h2>Optional: GitHub OAuth (import / PRs)</h2>
      <p>
        The stack starts without secrets. For GitHub import and PRs, create a local{" "}
        <code>.env</code>:
      </p>
      <pre>
        <code>{`GITHUB_CLIENT_ID=your_id
GITHUB_CLIENT_SECRET=your_secret
# OAuth callback: http://127.0.0.1:8000/auth/github/callback`}</code>
      </pre>
      <p>
        Then run with <code>--env-file .env</code> added to the same compose command, e.g.{" "}
        <code>{`${DOCKER_QUICKSTART.slice(0, -5)} --env-file .env up -d`}</code>.
      </p>

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
        <li>Open Models and select Local Ollama (or another free endpoint).</li>
        <li>Optional: connect GitHub if you set OAuth secrets.</li>
        <li>Import a repository URL.</li>
      </ol>
    </>
  );
}
