"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import {
  ApiError,
  api,
  GITHUB_LOGIN_URL,
  REFRESH_INTERVAL_MS,
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
  const [loggingOut, setLoggingOut] = useState(false);

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

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await api.logout();
    } catch {
      /* still clear local auth feel */
    } finally {
      setAuthenticated(false);
      setRepositories([]);
      setLoggingOut(false);
    }
  }

  return (
    <AppShell
      right={
        authenticated ? (
          <>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => void loadRepositories()} disabled={loadingRepositories}>
              {loadingRepositories ? "Refreshing…" : "Refresh"}
            </button>
            <button className="btn btn-outline btn-sm" type="button" onClick={() => void handleLogout()} disabled={loggingOut}>
              {loggingOut ? "Logging out…" : "Log out"}
            </button>
          </>
        ) : sessionChecked ? (
          <a className="btn btn-primary btn-sm" href={GITHUB_LOGIN_URL}>
            Connect GitHub
          </a>
        ) : (
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Checking…
          </span>
        )
      }
    >
      {!sessionChecked ? (
        <p className="loading-line">Checking your Otter session…</p>
      ) : !authenticated ? (
        <div className="auth-gate">
          <div className="connect-panel">
            <p className="eyebrow">Workspace</p>
            <h1>Connect to open your workspace</h1>
            <p className="muted">Sign in with GitHub to import repositories and use Otter.</p>
            <div style={{ marginTop: "1.25rem" }}>
              <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
                Connect GitHub
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div className="stack">
          <div className="page-header">
            <div>
              <p className="eyebrow">Workspace</p>
              <h1>Repositories</h1>
              <p className="muted" style={{ margin: "0.4rem 0 0" }}>
                {lastSyncedAt ? `Last synced ${lastSyncedAt}` : "Waiting for first sync…"}
              </p>
            </div>
          </div>

          <section className="panel">
            <h2>Import a repository</h2>
            <p className="muted" style={{ marginTop: 0 }}>
              Paste a GitHub URL. Otter will clone and prepare it for intelligence, chat, and planning.
            </p>
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
            <h2>Your repositories</h2>
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
                    <div className="repo-row-meta">
                      <span>
                        {repo.branch
                          ? `branch / ${repo.branch}`
                          : repo.status === "queued"
                            ? "awaiting worker"
                            : repo.status === "cloning"
                              ? "cloning now"
                              : repo.status === "failed"
                                ? "import failed"
                                : "preparing"}
                      </span>
                      <span>{repo.file_count ? `${repo.file_count} files` : "—"}</span>
                    </div>
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
