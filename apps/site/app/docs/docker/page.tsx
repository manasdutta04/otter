import { CopyCommand } from "../../../components/CopyCommand";
import { InstallTabs } from "../../../components/InstallTabs";
import {
  DOCKER_HUB,
  DOCKER_IMAGE,
  DOCKER_PULL,
  DOCKER_QUICKSTART,
  GITHUB_REPO,
  PUBLIC_SITE,
} from "../../../lib/urls";

export default function DockerDocsPage() {
  return (
    <>
      <h1>Docker</h1>
      <p className="lead">
        Otter ships a public image on Docker Hub. End users pull and run Compose — no GitHub clone
        required. Contributors who want bind mounts should use{" "}
        <code>docker/compose.dev.yml</code> from the{" "}
        <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
          repo
        </a>
        .
      </p>

      <h2>Pull &amp; install tabs</h2>
      <InstallTabs size="docs" showDocker defaultTab="docker" />
      <p className="muted">
        Docker tab: <code>{DOCKER_PULL}</code>. Package-manager tabs install the standalone CLI.
      </p>

      <h2>Full stack (UI + API + DB)</h2>
      <pre>
        <code>{`docker compose -f ${PUBLIC_SITE}/docker-compose.yml up -d`}</code>
      </pre>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />
      <p className="muted" style={{ marginTop: "0.85rem" }}>
        This docs build resolves to: <code>{DOCKER_QUICKSTART}</code>
      </p>
      <p>
        Image:{" "}
        <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
          <code>{DOCKER_IMAGE}</code>
        </a>
        . Compose creates local Postgres + Redis volumes automatically.
      </p>
      <p>
        On Windows, if Compose fails resolving <code>.env</code> from a URL, download{" "}
        <a href="/docker-compose.yml">/docker-compose.yml</a> first, then{" "}
        <code>docker compose -f docker-compose.yml up -d</code>.
      </p>

      <h2>What runs</h2>
      <ul>
        <li>
          <code>manasdutta04/otter</code> — Next.js UI (:3000), FastAPI (:8000), Celery worker,
          engineer core (<code>packages/agent</code>)
        </li>
        <li>
          Official <code>postgres:16-alpine</code> and <code>redis:7-alpine</code> (local volumes)
        </li>
      </ul>
      <p>
        Release notes: <a href="/docs/changelog">Changelog</a> (pull <code>:latest</code> or a{" "}
        <code>v*</code> tag after each publish).
      </p>

      <h2>GitHub Connect (no secrets in the image)</h2>
      <p>
        The published image does not contain GitHub App Client Secrets. Operators set{" "}
        <code>OTTER_AUTH_BROKER_URL</code> to the Cloudflare Worker that completes login. End users
        only click Connect — see <a href="/docs/github">GitHub</a>.
      </p>

      <h2>Public distribution</h2>
      <ul>
        <li>
          Source: public on{" "}
          <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </li>
        <li>
          Runtime image: public on{" "}
          <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
            Docker Hub
          </a>
        </li>
        <li>
          Compose file: public on this site (<code>{PUBLIC_SITE}/docker-compose.yml</code>)
        </li>
        <li>App credentials: only in Cloudflare Secrets for the auth broker</li>
      </ul>

      <h2>Ollama from Docker</h2>
      <p>
        Ollama stays on the host. The platform reaches it via{" "}
        <code>host.docker.internal:11434</code>. Do not use <code>127.0.0.1</code> inside the
        container for Ollama.
      </p>
    </>
  );
}
