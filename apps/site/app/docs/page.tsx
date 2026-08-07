import Link from "next/link";
import { CopyCommand } from "../../components/CopyCommand";

export default function DocsIndexPage() {
  return (
    <>
      <h1>Documentation</h1>
      <p className="lead">
        Otter is self-host first. No clone required — pull the Docker Hub image and start with one
        command. Product UI: <code>http://127.0.0.1:3000/app</code>.
      </p>

      <h2>Run Otter</h2>
      <CopyCommand useComposeUrl variant="button" className="docs-copy-pill" />

      <h2>Start here</h2>
      <ul>
        <li>
          <Link href="/docs/self-host">Self-host</Link> — one command + optional GitHub OAuth
        </li>
        <li>
          <Link href="/docs/docker">Docker</Link> — image, private-repo notes
        </li>
        <li>
          <Link href="/docs/models">Models</Link> — Ollama and OpenAI-compatible endpoints
        </li>
        <li>
          <Link href="/docs/github">GitHub</Link> — OAuth for import and PRs
        </li>
        <li>
          <Link href="/docs/cli">CLI</Link> — thin client status
        </li>
      </ul>
    </>
  );
}
