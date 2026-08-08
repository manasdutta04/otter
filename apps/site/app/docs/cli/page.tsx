import { SITE_URL } from "../../../lib/urls";

export default function CliDocsPage() {
  return (
    <>
      <h1>CLI</h1>
      <p className="lead">
        Otter CLI (<code>otter-engg</code>) is an interactive terminal product — splash, setup menus,
        then a session prompt. No Docker required.
      </p>

      <h2>Install</h2>
      <pre>
        <code>{`npm install -g otter-engg
# or
bun add -g otter-engg`}</code>
      </pre>

      <h2>Start</h2>
      <pre>
        <code>{`otter`}</code>
      </pre>
      <p>
        After the welcome animation and login/model setup, you land on{" "}
        <code>otter ›</code>. Type a task, or use slash commands.
      </p>

      <h2>Inside the session</h2>
      <ul>
        <li>
          Freeform prompts — coding agent with approval
        </li>
        <li>
          <code>/import owner/repo</code> · <code>/scan</code> · <code>/intel</code> ·{" "}
          <code>/health</code> · <code>/memory</code>
        </li>
        <li>
          <code>/model</code> · <code>/login</code> · <code>/exit</code>
        </li>
      </ul>

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
