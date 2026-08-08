import { CopyCommand } from "../../../components/CopyCommand";
import { InstallTabs } from "../../../components/InstallTabs";
import {
  CLI_INSTALL_NPM,
  DOCKER_HUB,
  DOCKER_IMAGE,
  DOCKER_PULL,
  DOCKER_QUICKSTART,
  NPM_PACKAGE,
} from "../../../lib/urls";

export default function SelfHostDocsPage() {
  return (
    <>
      <h1>Self-host</h1>
      <p className="lead">
        Two ways to run Otter locally: the Docker product UI (Postgres + API), or the standalone CLI
        (<code>{NPM_PACKAGE}</code>). Both use the Otter GitHub App for login.
      </p>

      <h2>Install</h2>
      <InstallTabs size="docs" showDocker defaultTab="docker" />

      <h2>Option A — Docker (full UI)</h2>
      <ol>
        <li>
          Pull: <code>{DOCKER_PULL}</code>
        </li>
        <li>Start Compose (local Postgres + Redis):</li>
      </ol>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />
      <p className="muted" style={{ marginTop: "0.85rem" }}>
        Or: <code>{DOCKER_QUICKSTART}</code>
      </p>
      <p>
        Open <code>http://127.0.0.1:3000/app</code>. Image:{" "}
        <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
          <code>{DOCKER_IMAGE}</code>
        </a>
        .
      </p>

      <h3>Requirements</h3>
      <ul>
        <li>Docker Engine + Compose v2</li>
        <li>Ollama on the host (recommended): <code>ollama pull qwen2.5-coder:7b</code></li>
      </ul>

      <h2>Option B — CLI only</h2>
      <pre>
        <code>{`${CLI_INSTALL_NPM}
otter`}</code>
      </pre>
      <p>
        No Docker. Storage under <code>~/.otter/</code>. See <a href="/docs/cli">CLI docs</a> for
        slash commands. Bun users: <code>bun add -g {NPM_PACKAGE}</code> (same npm package).
      </p>

      <h2>Connect GitHub</h2>
      <p>
        In the Docker UI click <strong>Connect GitHub</strong>, or in the CLI run{" "}
        <code>otter login</code> / <code>/login</code>. You install the Otter GitHub App — you do{" "}
        <strong>not</strong> paste Client secrets or create your own OAuth app. Details:{" "}
        <a href="/docs/github">GitHub docs</a>.
      </p>

      <h2>Open the product UI (Docker)</h2>
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
        <li>Install via Docker pull or npm CLI.</li>
        <li>Connect GitHub (Otter app).</li>
        <li>Point models at Local Ollama (or OpenAI-compatible).</li>
        <li>Import a repository.</li>
      </ol>
    </>
  );
}
