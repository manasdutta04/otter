export default function GitHubDocsPage() {
  return (
    <>
      <h1>GitHub</h1>
      <p className="lead">
        Connect with the <strong>Otter GitHub App</strong> so import and pull requests work. You do not
        create your own OAuth app. App secrets live on Otter&apos;s Cloudflare auth broker — not in
        your Docker image.
      </p>

      <h2>What you do (end user)</h2>
      <ol>
        <li>
          Start the local stack with Docker (see <a href="/docs/self-host">Self-host</a>). Postgres is
          created automatically in Docker.
        </li>
        <li>
          In the product UI click <strong>Connect GitHub</strong>, or with the standalone CLI run{" "}
          <code>otter login</code>.
        </li>
        <li>Install / authorize the Otter GitHub App when GitHub prompts you.</li>
        <li>Import a repo and open PRs after approving coding tasks.</li>
      </ol>

      <h2>Web · CLI · MCP</h2>
      <ul>
        <li>
          <strong>Web</strong> — Connect GitHub in the app chrome (cookie session; Docker stack).
        </li>
        <li>
          <strong>CLI</strong> — standalone <code>@otter-engg/cli</code>: <code>otter login</code>{" "}
          (same broker; session in <code>~/.otter/config.json</code>). No Docker required.
        </li>
        <li>
          <strong>MCP</strong> — uses <code>OTTER_SESSION</code> or reads <code>~/.otter/config.json</code>{" "}
          after CLI login. Point <code>OTTER_API_URL</code> at the Docker API if you use MCP tools
          against the web stack.
        </li>
      </ul>

      <h2>Privacy</h2>
      <ul>
        <li>Repository clones and the database stay on your machine (Docker volumes).</li>
        <li>Cloudflare only completes GitHub App login and returns a short-lived one-time code.</li>
        <li>Day-to-day chat / import / PRs talk to your local API only.</li>
      </ul>

      <h2>Operators (Otter maintainers)</h2>
      <p>
        Register the GitHub App and deploy the broker — see{" "}
        <code>apps/auth-broker/GITHUB_APP_SETUP.md</code> in the repo. Set{" "}
        <code>OTTER_AUTH_BROKER_URL</code> on the platform compose. Never put the Client Secret in
        Docker Hub.
      </p>
    </>
  );
}
