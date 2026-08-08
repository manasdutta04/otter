import { GITHUB_REPO } from "../../../lib/urls";

export default function GitHubDocsPage() {
  return (
    <>
      <h1>GitHub</h1>
      <p className="lead">
        Connect with the <strong>Otter GitHub App</strong> so import and pull requests work. You do
        not create your own OAuth app. App secrets live on Otter&apos;s Cloudflare auth broker —
        not in your Docker image or CLI package.
      </p>

      <h2>What you do (end user)</h2>
      <ol>
        <li>
          Start Docker (see <a href="/docs/self-host">Self-host</a>) or install the CLI (
          <code>npm i -g @otter-engg/cli</code>).
        </li>
        <li>
          In the product UI click <strong>Connect GitHub</strong>, or run{" "}
          <code>otter login</code> / <code>/login</code> in the CLI.
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
          <strong>MCP</strong> — uses <code>OTTER_SESSION</code> or reads{" "}
          <code>~/.otter/config.json</code> after CLI login. Point <code>OTTER_API_URL</code> at the
          Docker API if you use MCP tools against the web stack. See{" "}
          <code>apps/mcp</code> in the{" "}
          <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
            repo
          </a>
          .
        </li>
      </ul>

      <h2>Is the Worker login link safe?</h2>
      <p>
        Yes. Opening a Cloudflare Worker URL for login is expected. That link only starts GitHub OAuth —
        it does not embed Client Secrets. After GitHub authorizes you, the broker hands a short-lived
        one-time code back to your local CLI or API. Day-to-day work stays on your machine.
      </p>

      <h2>Privacy</h2>
      <ul>
        <li>Repository clones and databases stay on your machine (Docker volumes or <code>~/.otter/</code>).</li>
        <li>Cloudflare only completes GitHub App login and returns a short-lived one-time code.</li>
        <li>Day-to-day chat / import / PRs talk to your local API or CLI only.</li>
      </ul>

      <h2>Operators &amp; contributors</h2>
      <p>
        The GitHub App and auth broker are maintained in this public monorepo under{" "}
        <code>apps/auth-broker</code> and <code>apps/github-app</code>. Never commit Client Secrets.
        See{" "}
        <a href={`${GITHUB_REPO}/blob/main/apps/auth-broker/README.md`} target="_blank" rel="noreferrer">
          auth-broker README
        </a>{" "}
        and <a href="/docs/contribute">Contribute</a>.
      </p>
    </>
  );
}
