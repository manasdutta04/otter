import Link from "next/link";
import { InstallTabs } from "../../components/InstallTabs";

export default function DocsIndexPage() {
  return (
    <>
      <h1>Documentation</h1>
      <p className="lead">
        Otter is self-host first. Use Docker for the full local UI + API, or install the standalone CLI
        from npm. Connect GitHub through the Otter GitHub App (Cloudflare broker).
      </p>

      <h2>Install</h2>
      <InstallTabs size="docs" showDocker defaultTab="npm" />
      <p className="muted">
        After Docker: open <code>http://127.0.0.1:3000/app</code>. After a package manager: run{" "}
        <code>otter</code>. pnpm / yarn / npm / bun all install the same npm package.
      </p>

      <h2>Start here</h2>
      <ul>
        <li>
          <Link href="/docs/self-host">Self-host</Link> — Docker stack + Connect GitHub + Models
        </li>
        <li>
          <Link href="/docs/cli">CLI</Link> — <code>@otter-engg/cli</code> interactive session
        </li>
        <li>
          <Link href="/docs/docker">Docker</Link> — image, compose, local DB
        </li>
        <li>
          <Link href="/docs/github">GitHub</Link> — Otter GitHub App for Web · CLI · MCP
        </li>
        <li>
          <Link href="/docs/models">Models</Link> — Ollama and OpenAI-compatible endpoints
        </li>
      </ul>
    </>
  );
}
