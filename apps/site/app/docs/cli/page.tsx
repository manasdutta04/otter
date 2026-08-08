import { InstallTabs } from "../../../components/InstallTabs";
import {
  CLI_INSTALL_NPM_GLOBAL,
  NPM_PACKAGE,
  SITE_URL,
} from "../../../lib/urls";

export default function CliDocsPage() {
  return (
    <>
      <h1>CLI</h1>
      <p className="lead">
        Otter CLI (<code>{NPM_PACKAGE}</code>) is an interactive terminal product — splash, setup
        menus, then a session prompt. No Docker required. Data lives under{" "}
        <code>~/.otter/</code>.
      </p>

      <h2>Install</h2>
      <InstallTabs size="docs" defaultTab="npm" />
      <p>
        For a global binary on PATH, prefer{" "}
        <code>{CLI_INSTALL_NPM_GLOBAL}</code>. Tabs use the same{" "}
        <a href="https://chanhdai.com/components/code-block-command" target="_blank" rel="noreferrer">
          Code Block Command
        </a>{" "}
        pattern (pnpm / yarn / npm / bun). Bun installs the same npm package — we do not publish a
        separate Bun package.
      </p>

      <h2>Start</h2>
      <pre>
        <code>{`otter`}</code>
      </pre>
      <p>
        After the welcome animation and login/model setup, you land on{" "}
        <code>otter ›</code>. Type a task, or use slash commands.
      </p>

      <h2>Slash commands</h2>
      <h3>Understand</h3>
      <ul>
        <li>
          <code>/scan</code> — scan workspace
        </li>
        <li>
          <code>/intel</code> — intelligence report
        </li>
        <li>
          <code>/health</code> — health report
        </li>
        <li>
          <code>/review</code> — code review
        </li>
        <li>
          <code>/docs</code> — generate overview docs
        </li>
      </ul>
      <h3>Ask &amp; plan</h3>
      <ul>
        <li>
          <code>/chat &lt;question&gt;</code>
        </li>
        <li>
          <code>/plan &lt;request&gt;</code>
        </li>
        <li>
          <code>/memory [add &lt;note&gt;]</code>
        </li>
      </ul>
      <h3>Build</h3>
      <ul>
        <li>
          <code>/create &lt;request&gt; [--pr] [--yes]</code> — code + optional PR
        </li>
        <li>
          <code>/pr</code> — open PR for current local changes
        </li>
      </ul>
      <h3>Repos &amp; session</h3>
      <ul>
        <li>
          <code>/import owner/repo</code> — clone from GitHub
        </li>
        <li>
          <code>/model [name]</code> · <code>/login</code> · <code>/logout</code>
        </li>
        <li>
          <code>/clear</code> · <code>/help</code> · <code>/exit</code>
        </li>
      </ul>
      <p>Freeform prompts run the coding agent with approval before writes.</p>

      <h2>Models</h2>
      <p>
        Default Ollama at <code>http://127.0.0.1:11434/v1</code>. Pick models during setup or with{" "}
        <code>/model</code>.
      </p>

      <p>
        Site: <a href={SITE_URL}>{SITE_URL}</a>
      </p>
    </>
  );
}
