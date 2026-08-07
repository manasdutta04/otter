export default function SelfHostDocsPage() {
  return (
    <>
      <h1>Self-host</h1>
      <p className="lead">
        Bring up Otter with Docker Compose, connect a local model, then import a repository.
      </p>

      <h2>Requirements</h2>
      <ul>
        <li>Docker Engine + Compose v2</li>
        <li>Ollama on the host (recommended): <code>ollama pull qwen2.5-coder:7b</code></li>
        <li>GitHub OAuth app for import / PR flows</li>
      </ul>

      <h2>Start the stack</h2>
      <pre>
        <code>{`cp .env.example .env
# Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
# OAuth callback: http://127.0.0.1:8000/auth/github/callback

docker compose -f docker/compose.platform.yml up --build -d`}</code>
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
      <p>
        The marketing site (this Vercel app) is separate. Docker only serves the product UI — there is
        no landing page inside the container.
      </p>

      <h2>First-run checklist</h2>
      <ol>
        <li>Open Models and select Local Ollama (or another free endpoint).</li>
        <li>Connect GitHub in the workspace.</li>
        <li>Import a repository URL.</li>
      </ol>
    </>
  );
}
