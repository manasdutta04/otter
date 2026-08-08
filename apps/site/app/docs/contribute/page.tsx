import { GITHUB_REPO } from "../../../lib/urls";

export default function ContributeDocsPage() {
  return (
    <>
      <h1>Contribute</h1>
      <p className="lead">
        Otter is public and MIT-licensed. Bug reports, docs improvements, and pull requests are
        welcome — as long as they support{" "}
        <em>understand → explain → plan → review → build (with approval)</em>.
      </p>

      <h2>Start here</h2>
      <ol>
        <li>
          Read{" "}
          <a href={`${GITHUB_REPO}/blob/main/CONTRIBUTING.md`} target="_blank" rel="noreferrer">
            CONTRIBUTING.md
          </a>{" "}
          in the repo
        </li>
        <li>
          Browse{" "}
          <a href={`${GITHUB_REPO}/issues`} target="_blank" rel="noreferrer">
            open issues
          </a>{" "}
          or open a new one for discussion
        </li>
        <li>
          Fork{" "}
          <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
            manasdutta04/otter
          </a>
          , branch, and open a focused PR
        </li>
      </ol>

      <h2>Good first areas</h2>
      <ul>
        <li>Docs and examples under <code>apps/site/app/docs</code></li>
        <li>CLI UX and slash commands in <code>apps/cli</code></li>
        <li>Product UI polish in <code>apps/web</code></li>
        <li>API tests and clarity in <code>apps/api</code></li>
        <li>MCP / VS Code bridges</li>
      </ul>

      <h2>Local setup (short)</h2>
      <pre>
        <code>{`git clone https://github.com/manasdutta04/otter.git
cd otter
cp .env.example .env

# Full stack with bind mounts
docker compose -f docker/compose.dev.yml up --build

# Docs site only
cd apps/site && npm install && npm run dev`}</code>
      </pre>

      <h2>Community</h2>
      <ul>
        <li>
          <a href={`${GITHUB_REPO}/blob/main/CODE_OF_CONDUCT.md`} target="_blank" rel="noreferrer">
            Code of Conduct
          </a>
        </li>
        <li>
          <a href={`${GITHUB_REPO}/blob/main/SECURITY.md`} target="_blank" rel="noreferrer">
            Security policy
          </a>{" "}
          — please report vulnerabilities privately
        </li>
        <li>
          License:{" "}
          <a href={`${GITHUB_REPO}/blob/main/LICENSE`} target="_blank" rel="noreferrer">
            MIT
          </a>
        </li>
      </ul>
    </>
  );
}
