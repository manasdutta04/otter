"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { AppSidebar } from "../../components/AppSidebar";
import { EmptyState } from "../../components/EmptyState";
import { ModelStatusChip } from "../../components/ModelStatusChip";
import { StatusBadge } from "../../components/StatusBadge";
import { WorkMachine } from "../../components/WorkMachine";
import {
  ApiError,
  api,
  GITHUB_LOGIN_URL,
  REFRESH_INTERVAL_MS,
  type LlmTestResult,
  type Repository,
} from "../../lib/api";

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function AppDashboardPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [url, setUrl] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [loadingRepositories, setLoadingRepositories] = useState(false);
  const [importing, setImporting] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [llmTest, setLlmTest] = useState<LlmTestResult | null>(null);

  const loadRepositories = useCallback(async () => {
    if (!authenticated) return;
    setLoadingRepositories(true);
    try {
      const data = await api.listRepositories();
      setRepositories(data.repositories);
      setLastSyncedAt(formatTime(new Date()));
      setError("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setAuthenticated(false);
        setRepositories([]);
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load repositories");
    } finally {
      setLoadingRepositories(false);
    }
  }, [authenticated]);

  const loadSession = useCallback(async () => {
    try {
      const data = await api.getMe();
      setAuthenticated(Boolean(data.authenticated));
    } catch {
      setAuthenticated(false);
    } finally {
      setSessionChecked(true);
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    void (async () => {
      try {
        setLlmTest(await api.testLlmSettings());
      } catch {
        setLlmTest(null);
      }
    })();
  }, []);

  useEffect(() => {
    if (!sessionChecked || !authenticated) return;
    void loadRepositories();
    const interval = window.setInterval(() => {
      void loadRepositories();
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [authenticated, loadRepositories, sessionChecked]);

  async function importRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setImporting(true);
    try {
      await api.createRepository(url.trim());
      setUrl("");
      await loadRepositories();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start the import right now.");
    } finally {
      setImporting(false);
    }
  }

  return (
    <AppShell
      sidebar={<AppSidebar />}
      title={
        <div>
          <h1 className="product-page-title">Repositories</h1>
        </div>
      }
      right={
        sessionChecked ? (
          <>
            <ModelStatusChip />
            {authenticated ? (
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={() => void loadRepositories()}
                disabled={loadingRepositories}
              >
                {loadingRepositories ? "Refreshing…" : "Refresh"}
              </button>
            ) : null}
          </>
        ) : (
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Checking…
          </span>
        )
      }
    >
      {!sessionChecked ? (
        <p className="loading-line">Checking session…</p>
      ) : !authenticated ? (
        <div className="auth-gate">
          <div className="connect-panel">
            <h1>Connect GitHub to import repos</h1>
            <p className="muted">
              Set a model under Models, then connect GitHub from the sidebar for clone and PR access.
            </p>
            <div className="connect-actions">
              <Link className="btn btn-outline" href="/app/models">
                Choose model
              </Link>
              <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
                Connect GitHub
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div className="stack workspace-home">
          <p className="muted workspace-sync">
            {lastSyncedAt ? `Last synced ${lastSyncedAt}` : "Waiting for first sync…"}
          </p>

          {llmTest && !llmTest.ok ? (
            <div className="model-banner">
              <div>
                <h2>Connect a model before coding</h2>
                <p className="muted">
                  {llmTest.detail || "Ollama is unreachable. Pull qwen2.5-coder:7b and open Models."}
                </p>
              </div>
              <Link className="btn btn-primary btn-sm" href="/app/models">
                Open Models
              </Link>
            </div>
          ) : null}

          <section className="panel import-panel">
            <div className="panel-head">
              <div>
                <h2>Import a repository</h2>
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  Paste a GitHub URL. Otter clones it for intelligence, chat, and coding.
                </p>
              </div>
            </div>
            <form className="inline-form" onSubmit={(e) => void importRepository(e)}>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                required
                disabled={importing}
                aria-label="GitHub repository URL"
              />
              <button className="btn btn-primary" type="submit" disabled={importing}>
                {importing ? "Importing…" : "Import"}
              </button>
            </form>
            {error ? <p className="error-text">{error}</p> : null}
          </section>

          <section className="panel">
            <div className="panel-head">
              <h2>Your repositories</h2>
              <span className="muted">{repositories.length ? `${repositories.length} total` : null}</span>
            </div>
            {repositories.length === 0 ? (
              <EmptyState
                title="No repositories yet"
                detail="Import a GitHub URL above. Status updates automatically every few seconds."
              />
            ) : (
              <div className="repo-list">
                {repositories.map((repo) => (
                  <Link className="repo-row" href={`/app/repositories/${repo.id}`} key={repo.id}>
                    <div>
                      <h3>{repo.name}</h3>
                      <p>{repo.url.replace("https://github.com/", "")}</p>
                    </div>
                    <StatusBadge status={repo.status} />
                    {repo.status === "queued" || repo.status === "cloning" ? (
                      <WorkMachine mode="import" status={repo.status} compact />
                    ) : (
                      <div className="repo-row-meta">
                        <span>
                          {repo.branch
                            ? `branch / ${repo.branch}`
                            : repo.status === "failed"
                              ? "import failed"
                              : "preparing"}
                        </span>
                        <span>{repo.file_count ? `${repo.file_count} files` : "—"}</span>
                      </div>
                    )}
                    {repo.error ? (
                      <p className="error-text" style={{ gridColumn: "1 / -1", margin: 0 }}>
                        {repo.error}
                      </p>
                    ) : null}
                  </Link>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
