import { CopyCommand } from "../../../components/CopyCommand";
import { InstallTabs } from "../../../components/InstallTabs";
import {
  CLI_INSTALL_NPM,
  DOCKER_HUB,
  DOCKER_IMAGE,
  DOCKER_PULL,
  DOCKER_QUICKSTART,
  GITHUB_REPO,
  NPM_PACKAGE,
  PUBLIC_SITE,
} from "../../../lib/urls";

export default function SelfHostDocsPage() {
  return (
    <>
      <h1>Self-host</h1>
      <p className="lead">
        Run Otter on your machine in a few minutes. No need to clone the repo unless you want to
        contribute — pull the public image or install the CLI from npm.
      </p>

      <h2>Install</h2>
      <InstallTabs size="docs" showDocker defaultTab="docker" />

      <h2>Option A — Docker (full UI)</h2>
      <ol>
        <li>
          Pull: <code>{DOCKER_PULL}</code>
        </li>
        <li>Start Compose (creates local Postgres + Redis):</li>
      </ol>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />
      <p className="muted" style={{ marginTop: "0.85rem" }}>
        Canonical compose URL:{" "}
        <code>
          docker compose -f {PUBLIC_SITE}/docker-compose.yml up -d
        </code>
      </p>
      <p className="muted">
        Fallback (same host as this docs build): <code>{DOCKER_QUICKSTART}</code>
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

      <h3>Windows note</h3>
      <p>
        If Compose fails resolving <code>.env</code> from a remote URL, download{" "}
        <a href="/docker-compose.yml">docker-compose.yml</a> first, then run{" "}
        <code>docker compose -f docker-compose.yml up -d</code>.
      </p>

      <h2>Option B — CLI only</h2>
      <pre>
        <code>{`${CLI_INSTALL_NPM}
otter`}</code>
      </pre>
      <p>
        No Docker. Storage under <code>~/.otter/</code>. See <a href="/docs/cli">CLI docs</a> for
        slash commands. Same package for pnpm / yarn / bun.
      </p>

      <h2>Connect GitHub</h2>
      <p>
        In the Docker UI click <strong>Connect GitHub</strong>, or in the CLI run{" "}
        <code>otter login</code> / <code>/login</code>. You install the Otter GitHub App — you do{" "}
        <strong>not</strong> paste Client secrets. Details: <a href="/docs/github">GitHub docs</a>.
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
        <li>Install via Docker pull or npm CLI (<code>{NPM_PACKAGE}</code>).</li>
        <li>Connect GitHub (Otter app).</li>
        <li>Point models at Local Ollama (or OpenAI-compatible).</li>
        <li>Import a repository.</li>
      </ol>

      <h2>Want to hack on Otter?</h2>
      <p>
        Clone{" "}
        <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
          the public repo
        </a>{" "}
        and see <a href="/docs/contribute">Contribute</a>.
      </p>
    </>
  );
}
