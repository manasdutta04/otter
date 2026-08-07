"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "../../../components/AppShell";
import { ModelStatusChip } from "../../../components/ModelStatusChip";
import { api, type LlmProvider, type LlmSettings, type LlmTestResult } from "../../../lib/api";

const OLLAMA_DEFAULT = "http://host.docker.internal:11434/v1";

export default function ModelsPage() {
  const [provider, setProvider] = useState<LlmProvider>("ollama");
  const [baseUrl, setBaseUrl] = useState(OLLAMA_DEFAULT);
  const [model, setModel] = useState("qwen2.5-coder:7b");
  const [apiKey, setApiKey] = useState("");
  const [freeFailover, setFreeFailover] = useState(true);
  const [models, setModels] = useState<string[]>([]);
  const [settings, setSettings] = useState<LlmSettings | null>(null);
  const [test, setTest] = useState<LlmTestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const hydrate = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const current = await api.getLlmSettings();
      setSettings(current);
      setProvider(current.provider);
      setBaseUrl(current.base_url || OLLAMA_DEFAULT);
      setModel(current.model || "qwen2.5-coder:7b");
      setFreeFailover(current.free_failover);
      setApiKey("");
      const listed = await api.listLlmModels();
      setModels(listed.models);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load model settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  function chooseProvider(next: LlmProvider) {
    setProvider(next);
    setMessage("");
    if (next === "ollama") {
      setBaseUrl((prev) => (prev.includes("11434") || prev.includes("ollama") ? prev : OLLAMA_DEFAULT));
    }
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const saved = await api.saveLlmSettings({
        provider,
        base_url: baseUrl.trim(),
        model: model.trim(),
        api_key: apiKey.trim() ? apiKey.trim() : null,
        free_failover: freeFailover,
        keep_existing_key: !apiKey.trim() && Boolean(settings?.api_key_set),
      });
      setSettings(saved);
      setMessage("Saved. Otter will use this model for chat, explain, and coding.");
      setApiKey("");
      const listed = await api.listLlmModels();
      setModels(listed.models);
      const result = await api.testLlmSettings();
      setTest(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError("");
    try {
      // Persist first so test hits the intended config
      await api.saveLlmSettings({
        provider,
        base_url: baseUrl.trim(),
        model: model.trim(),
        api_key: apiKey.trim() ? apiKey.trim() : null,
        free_failover: freeFailover,
        keep_existing_key: !apiKey.trim() && Boolean(settings?.api_key_set),
      });
      const result = await api.testLlmSettings();
      setTest(result);
      const listed = await api.listLlmModels();
      setModels(listed.models);
      if (!result.ok) {
        setError(result.detail || "Model check failed");
      } else {
        setMessage(result.detail || "Connection ok");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTesting(false);
    }
  }

  return (
    <AppShell
      left={
        <nav className="studio-links" aria-label="Studio">
          <Link href="/app">Workspace</Link>
          <Link href="/app/models" className="active">
            Models
          </Link>
        </nav>
      }
      right={<ModelStatusChip />}
    >
      <div className="stack models-page">
        <div className="page-header">
          <div>
            <p className="eyebrow">Model Providers</p>
            <h1>Connect a free local model</h1>
            <p className="muted" style={{ margin: "0.45rem 0 0", maxWidth: "36rem" }}>
              After Docker is up, this is the only setup step. Prefer Ollama on the host — no paid API key required.
            </p>
          </div>
        </div>

        {loading ? (
          <p className="loading-line">Loading providers…</p>
        ) : (
          <form className="stack" onSubmit={(e) => void handleSave(e)}>
            <section className="provider-grid" aria-label="Provider choice">
              <button
                type="button"
                className={provider === "ollama" ? "provider-card active" : "provider-card"}
                onClick={() => chooseProvider("ollama")}
              >
                <strong>Local Ollama</strong>
                <span>Recommended · free · runs on your machine</span>
              </button>
              <button
                type="button"
                className={provider === "openai_compatible" ? "provider-card active" : "provider-card"}
                onClick={() => chooseProvider("openai_compatible")}
              >
                <strong>OpenAI-compatible</strong>
                <span>Self-hosted or free OpenAI-style endpoints</span>
              </button>
            </section>

            <section className="panel">
              <h2>Endpoint</h2>
              <div className="form-stack">
                <div className="field">
                  <label htmlFor="base-url">Base URL</label>
                  <input
                    id="base-url"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder={provider === "ollama" ? OLLAMA_DEFAULT : "https://api.example.com/v1"}
                    required
                  />
                  {provider === "ollama" ? (
                    <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                      In Docker use <code>host.docker.internal</code>. Native: <code>http://127.0.0.1:11434/v1</code>.
                      Pull a model: <code>ollama pull qwen2.5-coder:7b</code>
                    </p>
                  ) : null}
                </div>

                <div className="field">
                  <label htmlFor="model">Model</label>
                  {models.length > 0 ? (
                    <select id="model" value={model} onChange={(e) => setModel(e.target.value)}>
                      {!models.includes(model) ? <option value={model}>{model}</option> : null}
                      {models.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id="model"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      placeholder="qwen2.5-coder:7b"
                      required
                    />
                  )}
                </div>

                {provider === "openai_compatible" ? (
                  <div className="field">
                    <label htmlFor="api-key">API key {settings?.api_key_set ? `(saved ${settings.api_key_masked})` : ""}</label>
                    <input
                      id="api-key"
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder={settings?.api_key_set ? "Leave blank to keep existing" : "Optional for some free hosts"}
                      autoComplete="off"
                    />
                  </div>
                ) : null}

                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={freeFailover}
                    onChange={(e) => setFreeFailover(e.target.checked)}
                  />
                  Try failover local models when the primary fails
                </label>
              </div>

              <div className="task-actions" style={{ marginTop: "1.1rem" }}>
                <button className="btn btn-primary" type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save"}
                </button>
                <button className="btn btn-outline" type="button" disabled={testing} onClick={() => void handleTest()}>
                  {testing ? "Testing…" : "Test connection"}
                </button>
                <Link className="btn btn-ghost" href="/app">
                  Back to workspace
                </Link>
              </div>

              {message ? <p className="ok-text">{message}</p> : null}
              {error ? <p className="error-text">{error}</p> : null}
              {test ? (
                <div className={`llm-status ${test.ok ? "ok" : "bad"}`}>
                  <strong>{test.ok ? "Ready" : "Not ready"}</strong>
                  <span>
                    {test.reachable ? "Reachable" : "Unreachable"}
                    {test.completion_ok ? " · completion ok" : ""}
                    {test.detail ? ` — ${test.detail}` : ""}
                  </span>
                </div>
              ) : null}
            </section>
          </form>
        )}
      </div>
    </AppShell>
  );
}
