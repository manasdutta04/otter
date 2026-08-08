import Link from "next/link";
import { InstallTabs } from "../../../components/InstallTabs";
import { CLI_INSTALL_NPM_GLOBAL, NPM_PACKAGE } from "../../../lib/urls";

export default function FirstRunDocsPage() {
  return (
    <>
      <h1>First 10 minutes</h1>
      <p className="lead">
        Get from zero to a grounded chat (and an optional approved patch) on your machine. Pick
        Docker for the full UI, or the CLI if you prefer the terminal.
      </p>

      <h2>1. Install</h2>
      <InstallTabs size="docs" showDocker defaultTab="docker" />
      <p className="muted">
        Docker: open <code>http://127.0.0.1:3000/app</code>. CLI: run <code>otter</code> after{" "}
        <code>{CLI_INSTALL_NPM_GLOBAL}</code> (same package for pnpm / yarn / bun).
      </p>

      <h2>2. Connect GitHub</h2>
      <p>
        In the UI click <strong>Connect GitHub</strong>, or in the CLI run <code>/login</code>. You
        install the Otter GitHub App — you do not paste Client secrets. Details:{" "}
        <Link href="/docs/github">GitHub</Link>.
      </p>

      <h2>3. Point at a model</h2>
      <p>
        Recommended: Ollama on the host — <code>ollama pull qwen2.5-coder:7b</code>. In Docker open{" "}
        <code>http://127.0.0.1:3000/app/models</code> and choose Local Ollama. In the CLI use{" "}
        <code>/model</code>. More: <Link href="/docs/models">Models</Link>.
      </p>

      <h2>4. Import a repository</h2>
      <p>
        From the workspace, import a GitHub repo (or <code>/import owner/repo</code> in the CLI).
        Otter builds intelligence — stack, entry points, architecture signals — before any coding.
      </p>

      <h2>5. Ask, plan, then approve</h2>
      <ul>
        <li>
          <strong>Chat</strong> — ask how something works; answers cite real files.
        </li>
        <li>
          <strong>Planner</strong> — request a change; review steps and risks.
        </li>
        <li>
          <strong>Coding</strong> — link the plan, generate a patch, approve, apply, optional PR.
        </li>
        <li>
          CLI: <code>/create …</code> follows the same plan → approve → implement path.
        </li>
      </ul>

      <h2>What stays local</h2>
      <p>
        Repos, patches, and model traffic stay on your machine (or your chosen LLM endpoint). Otter
        is self-host first — see <Link href="/docs/self-host">Self-host</Link> for the full checklist
        and <Link href="/docs/docker">Docker</Link> / <Link href="/docs/cli">CLI</Link> for surface
        details. Package: <code>{NPM_PACKAGE}</code>.
      </p>
    </>
  );
}
