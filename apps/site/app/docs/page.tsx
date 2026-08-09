import Link from "next/link";
import { InstallTabs } from "../../components/InstallTabs";
import { GITHUB_REPO, NPM_PACKAGE, PUBLIC_SITE, PYPI_PACKAGE, PYPI_URL } from "../../lib/urls";

export default function DocsIndexPage() {
  return (
    <>
      <h1>Documentation</h1>
      <p className="lead">
        Otter is open source and self-host first. Run the full local UI with Docker, the standalone
        CLI from npm, or MCP from PyPI. Source, issues, and PRs:{" "}
        <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
          github.com/manasdutta04/otter
        </a>
        .
      </p>

      <h2>Install</h2>
      <InstallTabs size="docs" showDocker defaultTab="npm" />
      <p className="muted">
        After Docker: open <code>http://127.0.0.1:3000/app</code>. After a package manager: run{" "}
        <code>otter</code> (install uses <code>-g</code> so the binary is on your PATH). For Cursor /
        Claude: <code>pip install {PYPI_PACKAGE}</code> — see <Link href="/docs/mcp">MCP</Link>.
      </p>

      <h2>Guides</h2>
      <ul>
        <li>
          <Link href="/docs/first-run">First 10 minutes</Link> — install → GitHub → model → import →
          approve
        </li>
        <li>
          <Link href="/docs/self-host">Self-host</Link> — Docker or CLI checklist
        </li>
        <li>
          <Link href="/docs/cli">CLI</Link> — <code>{NPM_PACKAGE}</code>, slash commands
        </li>
        <li>
          <Link href="/docs/mcp">MCP</Link> — <code>{PYPI_PACKAGE}</code> for Cursor / Claude (stdio)
        </li>
        <li>
          <Link href="/docs/changelog">Changelog</Link> — Docker image + npm CLI + PyPI MCP releases
        </li>
        <li>
          <Link href="/docs/docker">Docker</Link> — image, compose, local Postgres + Redis
        </li>
        <li>
          <Link href="/docs/github">GitHub</Link> — Otter GitHub App for Web · CLI · MCP
        </li>
        <li>
          <Link href="/docs/models">Models</Link> — Ollama and OpenAI-compatible endpoints
        </li>
        <li>
          <Link href="/docs/contribute">Contribute</Link> — setup, PRs, community standards
        </li>
      </ul>

      <h2>Links</h2>
      <ul>
        <li>
          Site: <a href={PUBLIC_SITE}>{PUBLIC_SITE}</a>
        </li>
        <li>
          Docker Hub:{" "}
          <a href="https://hub.docker.com/r/manasdutta04/otter" target="_blank" rel="noreferrer">
            manasdutta04/otter
          </a>
        </li>
        <li>
          npm:{" "}
          <a href={`https://www.npmjs.com/package/${NPM_PACKAGE}`} target="_blank" rel="noreferrer">
            {NPM_PACKAGE}
          </a>
        </li>
        <li>
          PyPI:{" "}
          <a href={PYPI_URL} target="_blank" rel="noreferrer">
            {PYPI_PACKAGE}
          </a>
        </li>
      </ul>
    </>
  );
}
