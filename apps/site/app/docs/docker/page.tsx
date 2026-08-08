import { CopyCommand } from "../../../components/CopyCommand";
import { InstallTabs } from "../../../components/InstallTabs";
import {
  DOCKER_HUB,
  DOCKER_IMAGE,
  DOCKER_PULL,
  DOCKER_QUICKSTART,
} from "../../../lib/urls";

export default function DockerDocsPage() {
  return (
    <>
      <h1>Docker</h1>
      <p className="lead">
        Pull the public image{" "}
        <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
          <code>{DOCKER_IMAGE}</code>
        </a>
        . For the full UI stack, start Compose from this site (
        <code>/docker-compose.yml</code>) — it creates local Postgres + Redis automatically.
      </p>

      <h2>Pull</h2>
      <InstallTabs size="docs" showDocker defaultTab="docker" />
      <p className="muted">
        Docker tab: <code>{DOCKER_PULL}</code>. npm/bun tabs install the standalone CLI (no Docker).
      </p>

      <h2>Full stack (UI + API + DB)</h2>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />
      <p className="muted" style={{ marginTop: "0.85rem" }}>
        Fallback: <code>{DOCKER_QUICKSTART}</code>
      </p>
      <p>
        On Windows, if Compose fails resolving <code>.env</code> from a URL, download{" "}
        <code>/docker-compose.yml</code> first, then <code>docker compose -f docker-compose.yml up -d</code>.
      </p>

      <h2>What runs</h2>
      <ul>
        <li>
          <code>manasdutta04/otter</code> — Next.js UI (:3000), FastAPI (:8000), Celery worker
        </li>
        <li>
          Official <code>postgres:16-alpine</code> and <code>redis:7-alpine</code> (local volumes)
        </li>
      </ul>

      <h2>GitHub Connect (no secrets in the image)</h2>
      <p>
        Set <code>OTTER_AUTH_BROKER_URL</code> to the Cloudflare Worker that holds the Otter GitHub
        App secret. End users only click Connect — see <a href="/docs/github">GitHub</a>.
      </p>

      <h2>If the GitHub repo is private</h2>
      <ul>
        <li>Keep the Docker Hub image <strong>public</strong>.</li>
        <li>Keep this marketing site public (hosts <code>/docker-compose.yml</code>).</li>
        <li>Keep App credentials only in Cloudflare Secrets.</li>
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
