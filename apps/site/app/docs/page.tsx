import Link from "next/link";
import { CopyCommand } from "../../components/CopyCommand";
import { DOCKER_QUICKSTART } from "../../lib/urls";

export default function DocsIndexPage() {
  return (
    <>
      <h1>Documentation</h1>
      <p className="lead">
        Otter is self-host first. This site is marketing and docs. The product UI runs on your machine
        via Docker at <code>http://127.0.0.1:3000/app</code>.
      </p>

      <h2>Run Otter</h2>
      <CopyCommand command={DOCKER_QUICKSTART} />

      <h2>Start here</h2>
      <ul>
        <li>
          <Link href="/docs/self-host">Self-host</Link> — compose up and open the workspace
        </li>
        <li>
          <Link href="/docs/docker">Docker</Link> — what the platform image runs
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
