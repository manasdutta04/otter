import Link from "next/link";
import { DOCKER_HUB, DOCKER_IMAGE, NPM_PACKAGE, PYPI_PACKAGE, PYPI_URL } from "../../../lib/urls";

export default function ChangelogPage() {
  return (
    <>
      <h1>Changelog</h1>
      <p className="lead">
        Production releases for the Docker image, Web/API, <code>{NPM_PACKAGE}</code>, and{" "}
        <a href={PYPI_URL} target="_blank" rel="noreferrer">
          {PYPI_PACKAGE}
        </a>
        .
      </p>

      <h2>
        MCP 0.2.0 — Engineering intelligence layer{" "}
        <span className="muted" style={{ fontWeight: 400, fontSize: "0.85em" }}>
          2026-08-09
        </span>
      </h2>
      <p>
        Official MCP stdio server on PyPI. External agents get impact analysis, architecture guard,
        verification, and approval-gated tasks — install without cloning the monorepo.
      </p>
      <h3>What to install</h3>
      <ul>
        <li>
          <code>pip install {PYPI_PACKAGE}</code> or <code>uvx {PYPI_PACKAGE}</code>
        </li>
        <li>
          Docs: <Link href="/docs/mcp">/docs/mcp</Link> ·{" "}
          <a href={PYPI_URL} target="_blank" rel="noreferrer">
            PyPI
          </a>
        </li>
      </ul>
      <h3>Highlights</h3>
      <ul>
        <li>
          Tools: understand, impact, change radar, guard, why, verify, review gate, task orchestration
        </li>
        <li>Writes require approval — no silent apply</li>
        <li>Bundled intelligence packages in the wheel (no <code>PYTHONPATH</code> hack)</li>
      </ul>

      <h2>
        0.2.0 — Engineer core{" "}
        <span className="muted" style={{ fontWeight: 400, fontSize: "0.85em" }}>
          2026-08-08
        </span>
      </h2>
      <p>
        Shared engineer loop: understand → plan → approve → implement → validate. Targeted edits
        preferred over full-file rewrites. Intelligence feeds coding context on the Docker path.
      </p>
      <h3>What to upgrade</h3>
      <ul>
        <li>
          Docker:{" "}
          <code>
            docker pull {DOCKER_IMAGE}
          </code>{" "}
          then recreate Compose (
          <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
            Hub
          </a>
          )
        </li>
        <li>
          CLI: <code>npm i -g {NPM_PACKAGE}@0.2.0</code> (or pnpm / yarn / bun)
        </li>
      </ul>
      <h3>Highlights</h3>
      <ul>
        <li>
          Web Coding: link a Planner plan, generate patch, approve, apply
        </li>
        <li>
          CLI <code>/create</code>: stage plan, confirm, implement, validate
        </li>
        <li>Platform image loads <code>packages/agent</code> correctly for self-host</li>
      </ul>
      <p>
        Full notes:{" "}
        <a
          href="https://github.com/manasdutta04/otter/blob/main/CHANGELOG.md"
          target="_blank"
          rel="noreferrer"
        >
          CHANGELOG.md
        </a>
        . Guides: <Link href="/docs/cli">CLI</Link> · <Link href="/docs/docker">Docker</Link> ·{" "}
        <Link href="/docs/mcp">MCP</Link>.
      </p>

      <h2>
        0.1.x{" "}
        <span className="muted" style={{ fontWeight: 400, fontSize: "0.85em" }}>
          earlier
        </span>
      </h2>
      <p>
        First public Hub image and npm CLI, GitHub App login via auth broker, self-host Compose.
      </p>
    </>
  );
}
