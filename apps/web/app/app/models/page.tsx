"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "../../../components/AppShell";
import { AppSidebar } from "../../../components/AppSidebar";
import { ModelStatusChip } from "../../../components/ModelStatusChip";
import { WorkMachine } from "../../../components/WorkMachine";
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
      try {
        setTest(await api.testLlmSettings());
      } catch {
        setTest(null);
      }
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

  async function persist() {
    return api.saveLlmSettings({
      provider,
      base_url: baseUrl.trim(),
      model: model.trim(),
      api_key: apiKey.trim() ? apiKey.trim() : null,
      free_failover: freeFailover,
      keep_existing_key: !apiKey.trim() && Boolean(settings?.api_key_set),
    });
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const saved = await persist();
      setSettings(saved);
      setMessage("Saved. Otter will use this model for chat, explain, and coding.");
      setApiKey("");
      const listed = await api.listLlmModels();
      setModels(listed.models);
      setTest(await api.testLlmSettings());
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
      await persist();
      const result = await api.testLlmSettings();
      setTest(result);
      const listed = await api.listLlmModels();
      setModels(listed.models);
      if (!result.ok) setError(result.detail || "Model check failed");
      else setMessage(result.detail || "Connection ok");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTesting(false);
    }
  }

  return (
    <AppShell
      sidebar={<AppSidebar />}
      title={<h1 className="product-page-title">Models</h1>}
      right={<ModelStatusChip />}
      narrow={false}
    >
      <div className="models-layout">
        <header className="models-hero">
          <div>
            <h2>Inference endpoint</h2>
            <p className="muted">
              Connect Local Ollama on the host, or any OpenAI-compatible base URL. Otter uses this for
              chat, explain, and coding.
            </p>
          </div>
          {test ? (
            <div className={`llm-status compact ${test.ok ? "ok" : "bad"}`} role="status">
              <strong>{test.ok ? "Ready" : "Not ready"}</strong>
              <span>
                {test.model ? `${test.model} · ` : ""}
                {test.detail || (test.reachable ? "Reachable" : "Unreachable")}
              </span>
            </div>
          ) : null}
        </header>

        {loading ? (
          <p className="loading-line">Loading providers…</p>
        ) : (
          <form className="models-grid" onSubmit={(e) => void handleSave(e)}>
            <aside className="models-providers" aria-label="Provider choice">
              <p className="product-rail-label">Provider</p>
              <button
                type="button"
                className={provider === "ollama" ? "provider-card active" : "provider-card"}
                onClick={() => chooseProvider("ollama")}
              >
                <span className="provider-card-kicker">Recommended</span>
                <strong>Local Ollama</strong>
                <span>Free · runs on your machine · no API key</span>
              </button>
              <button
                type="button"
                className={provider === "openai_compatible" ? "provider-card active" : "provider-card"}
                onClick={() => chooseProvider("openai_compatible")}
              >
                <span className="provider-card-kicker">Optional</span>
                <strong>OpenAI-compatible</strong>
                <span>Self-hosted gateway or free OpenAI-style APIs</span>
              </button>
              <div className="models-hint panel-soft">
                <p className="product-rail-label" style={{ padding: 0, marginBottom: "0.45rem" }}>
                  Host tips
                </p>
                <p className="muted" style={{ margin: 0 }}>
                  Docker: <code>host.docker.internal:11434</code>
                  <br />
                  Native: <code>127.0.0.1:11434</code>
                  <br />
                  <code>ollama pull qwen2.5-coder:7b</code>
                </p>
              </div>
            </aside>

            <section className="panel models-config">
              <div className="panel-head">
                <h2>Configuration</h2>
                {settings?.provider ? (
                  <span className="muted" style={{ fontSize: "0.85rem" }}>
                    Active: {settings.provider === "ollama" ? "Ollama" : "OpenAI-compatible"}
                  </span>
                ) : null}
              </div>
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
                  {models.length > 0 ? (
                    <p className="muted field-hint">{models.length} models discovered from the endpoint</p>
                  ) : (
                    <p className="muted field-hint">No models discovered yet — enter a name or test the connection</p>
                  )}
                </div>

                {provider === "openai_compatible" ? (
                  <div className="field">
                    <label htmlFor="api-key">
                      API key {settings?.api_key_set ? `(saved ${settings.api_key_masked})` : ""}
                    </label>
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
                  <input type="checkbox" checked={freeFailover} onChange={(e) => setFreeFailover(e.target.checked)} />
                  Try failover local models when the primary fails
                </label>
              </div>

              <div className="models-actions">
                <button className="btn btn-primary" type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Save"}
                </button>
                <button className="btn btn-outline" type="button" disabled={testing} onClick={() => void handleTest()}>
                  {testing ? "Testing…" : "Test connection"}
                </button>
                <Link className="btn btn-ghost" href="/app">
                  Open workspace
                </Link>
              </div>

              {testing ? <WorkMachine mode="model" compact label="Probing the inference endpoint…" /> : null}

              {message ? <p className="ok-text">{message}</p> : null}
              {error ? <p className="error-text">{error}</p> : null}
            </section>
          </form>
        )}
      </div>
    </AppShell>
  );
}
