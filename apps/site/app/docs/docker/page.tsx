export default function DockerDocsPage() {
  return (
    <>
      <h1>Docker</h1>
      <p className="lead">
        Production self-host uses one custom image (<code>manasdutta04/otter</code> on Docker Hub)
        plus official Postgres and Redis.
      </p>

      <h2>Image</h2>
      <ul>
        <li>
          Hub:{" "}
          <a href="https://hub.docker.com/r/manasdutta04/otter" target="_blank" rel="noreferrer">
            manasdutta04/otter
          </a>
        </li>
        <li>
          Tags: <code>latest</code>, <code>0.1.0</code>
        </li>
      </ul>
      <pre>
        <code>{`docker pull manasdutta04/otter:latest`}</code>
      </pre>

      <h2>Compose file</h2>
      <p>
        Use <code>docker/compose.platform.yml</code>. It publishes <code>127.0.0.1:3000</code> (web) and{" "}
        <code>127.0.0.1:8000</code> (API).
      </p>
      <pre>
        <code>{`docker compose -f docker/compose.platform.yml pull
docker compose -f docker/compose.platform.yml up -d`}</code>
      </pre>
      <p>
        To rebuild from source instead of pulling:{" "}
        <code>docker compose -f docker/compose.platform.yml up --build -d</code>
      </p>

      <h2>What runs inside the platform container</h2>
      <ul>
        <li>Next.js product UI (standalone) on port 3000</li>
        <li>FastAPI on port 8000</li>
        <li>Celery worker for import / coding jobs</li>
      </ul>

      <h2>Ollama from Docker</h2>
      <p>
        Ollama stays on the host. The platform container reaches it via{" "}
        <code>host.docker.internal:11434</code> (set as <code>PLATFORM_LLM_BASE_URL</code>). Do not point
        the container at <code>127.0.0.1</code> for Ollama — that is the container loopback.
      </p>

      <h2>Contributor stack</h2>
      <p>
        Bind-mount development uses <code>docker/compose.dev.yml</code>. Prefer{" "}
        <code>compose.platform.yml</code> for the product install path.
      </p>
    </>
  );
}
