import { CopyCommand } from "../../../components/CopyCommand";
import { DOCKER_HUB, DOCKER_IMAGE, DOCKER_QUICKSTART } from "../../../lib/urls";

export default function DockerDocsPage() {
  return (
    <>
      <h1>Docker</h1>
      <p className="lead">
        Users never need your private GitHub source. They pull{" "}
        <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
          <code>{DOCKER_IMAGE}</code>
        </a>{" "}
        and start via the public compose file on this site (
        <code>/docker-compose.yml</code>). Compose creates local Postgres + Redis automatically.
      </p>

      <h2>One command</h2>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />

      <h2>Pull only</h2>
      <CopyCommand command={`docker pull ${DOCKER_IMAGE}`} variant="button" className="docs-copy-pill" />

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
      <p>
        Fallback command: <code>{DOCKER_QUICKSTART}</code>
      </p>

      <h2>Ollama from Docker</h2>
      <p>
        Ollama stays on the host. The platform reaches it via{" "}
        <code>host.docker.internal:11434</code>. Do not use <code>127.0.0.1</code> inside the
        container for Ollama.
      </p>
    </>
  );
}
