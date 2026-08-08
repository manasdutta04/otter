import { APP_MODELS } from "../../../lib/urls";

export default function ModelsDocsPage() {
  return (
    <>
      <h1>Models</h1>
      <p className="lead">
        Otter does not host GPUs for you. Configure inference once in the local app under Models.
      </p>

      <h2>Local Ollama (recommended)</h2>
      <pre>
        <code>{`ollama pull qwen2.5-coder:7b
# Docker platform base URL: http://host.docker.internal:11434/v1
# Native / CLI base URL:    http://127.0.0.1:11434/v1`}</code>
      </pre>
      <p>
        Docker UI: open{" "}
        <a href={APP_MODELS}>
          <code>/app/models</code>
        </a>
        , choose Local Ollama, save, and test. CLI: run <code>/model</code> inside{" "}
        <code>otter</code>.
      </p>

      <h2>OpenAI-compatible</h2>
      <p>
        Any OpenAI-style <code>/v1</code> endpoint works. Paste the base URL, pick a model, and set an
        API key only if the host requires one.
      </p>

      <h2>Failover</h2>
      <p>
        Optional free failover tries alternate local models when the primary completion fails. Toggle it
        on the Models page.
      </p>
    </>
  );
}
