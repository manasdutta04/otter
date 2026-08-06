"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Repository = { id: string; name: string; url: string; status: "queued" | "cloning" | "ready" | "failed"; file_count: number; branch?: string | null; error?: string | null };
type RepositoryListResponse = { repositories: Repository[] };
type Intelligence = { summary: string; tech_stack: string[]; folders: string[]; entry_points: string[]; architecture_signals: string[] };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_INTERVAL_MS = 5000;

const STATUS_LABELS: Record<Repository["status"], string> = {
  queued: "Queued",
  cloning: "Cloning",
  ready: "Ready",
  failed: "Failed",
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Dashboard() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [url, setUrl] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [loadingRepositories, setLoadingRepositories] = useState(false);
  const [importing, setImporting] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [error, setError] = useState("");

  const metrics = useMemo(() => {
    const ready = repositories.filter((repository) => repository.status === "ready").length;
    const inProgress = repositories.filter((repository) => repository.status === "queued" || repository.status === "cloning").length;
    const failed = repositories.filter((repository) => repository.status === "failed").length;
    return { ready, inProgress, failed };
  }, [repositories]);

  const loadRepositories = useCallback(async () => {
    if (!authenticated) {
      return;
    }
    setLoadingRepositories(true);
    try {
      const response = await fetch(`${API_URL}/repositories`, { credentials: "include" });
      if (response.status === 401) {
        setAuthenticated(false);
        setRepositories([]);
        return;
      }
      if (!response.ok) {
        throw new Error("Unable to load repositories");
      }
      const data = (await response.json()) as RepositoryListResponse;
      setRepositories(data.repositories);
      setLastSyncedAt(formatTime(new Date()));
    } finally {
      setLoadingRepositories(false);
    }
  }, [authenticated]);

  const loadSession = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
      if (response.ok) {
        const data = (await response.json()) as { authenticated: boolean };
        setAuthenticated(Boolean(data.authenticated));
      } else {
        setAuthenticated(false);
      }
    } finally {
      setSessionChecked(true);
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    if (!sessionChecked || !authenticated) {
      return;
    }
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
      const response = await fetch(`${API_URL}/repositories`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.detail ?? "Import failed");
        return;
      }
      setUrl("");
      await loadRepositories();
    } catch {
      setError("Unable to start the import right now.");
    } finally {
      setImporting(false);
    }
  }

  return <main className="workspace-shell">
    <header className="topbar">
      <Link className="brand" href="/">
        <span className="brand-mark">◈</span>
        <span>veridexs</span>
      </Link>
      <div className="topbar-links">
        <span className={`status-pill ${authenticated ? "ready" : "failed"}`}>{authenticated ? "GitHub connected" : sessionChecked ? "GitHub disconnected" : "Checking session"}</span>
        {authenticated ? <button className="ghost-button" type="button" onClick={() => void loadRepositories()} disabled={loadingRepositories}>{loadingRepositories ? "Refreshing" : "Refresh"}</button> : <a className="login-link" href={`${API_URL}/auth/github/login`}>Connect GitHub ↗</a>}
      </div>
    </header>

    <section className="hero-grid">
      <div className="hero-copy">
        <p className="eyebrow">ENGINEERING INTELLIGENCE / WORKSPACE</p>
        <h1>Your codebase,<br /><em>made legible.</em></h1>
        <p className="intro">Import a repository, track it live, and move into a dedicated detail view for intelligence and chat. This is the first piece of the product shell the PRD calls for.</p>
      </div>
      <div className="hero-panel">
        <div className="metric-grid">
          <article className="metric-card"><span>Tracked</span><strong>{repositories.length.toString().padStart(2, "0")}</strong></article>
          <article className="metric-card"><span>Ready</span><strong>{metrics.ready.toString().padStart(2, "0")}</strong></article>
          <article className="metric-card"><span>Live</span><strong>{metrics.inProgress.toString().padStart(2, "0")}</strong></article>
          <article className="metric-card"><span>Failed</span><strong>{metrics.failed.toString().padStart(2, "0")}</strong></article>
        </div>
        <div className="hero-note">
          <span className="card-kicker">LIVE SYNC</span>
          <p>{lastSyncedAt ? `Last refreshed at ${lastSyncedAt}.` : "Waiting for the first repository refresh."}</p>
        </div>
      </div>
    </section>

    <section className="import-card">
      <div>
        <p className="card-kicker">START WITH A REPOSITORY</p>
        <h2>Bring a codebase into focus.</h2>
        <p className="muted">Paste a GitHub URL. veridexs will clone, inspect, and prepare it for the detail workspace.</p>
      </div>
      <form onSubmit={importRepository}>
        <label htmlFor="repo-url">GitHub repository URL</label>
        <div className="input-row">
          <input id="repo-url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://github.com/owner/repository" required disabled={!authenticated || importing} />
          <button disabled={!authenticated || importing}>{importing ? "Importing" : "Import repository"} <span>→</span></button>
        </div>
        {error && <p className="error">{error}</p>}
      </form>
    </section>

    <section className="workspace-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h2>Repositories</h2>
        </div>
        <span className="count">{loadingRepositories ? "syncing" : `${String(repositories.length).padStart(2, "0")} tracked`}</span>
      </div>

      {!sessionChecked ? <div className="empty-state"><span>◎</span><p>Checking your session…</p><small>The dashboard is verifying your GitHub connection before loading repositories.</small></div> : repositories.length === 0 ? <div className="empty-state"><span>◎</span><p>{authenticated ? "No repositories yet." : "Connect GitHub to see your workspace."}</p><small>Phase 01 combines import, repository intelligence, and contextual questions.</small></div> : <div className="repo-grid">{repositories.map((repo) => <Link className={`repo-card ${repo.status}`} href={`/repositories/${repo.id}`} key={repo.id}><div className="repo-icon">⌁</div><div className="repo-info"><h3>{repo.name}</h3><p>{repo.url.replace("https://github.com/", "")}</p></div><span className={`status-pill ${repo.status}`}>{STATUS_LABELS[repo.status]}</span><div className="repo-meta"><span>{repo.branch ? `branch / ${repo.branch}` : repo.status === "queued" ? "awaiting worker" : repo.status === "cloning" ? "cloning now" : repo.status === "failed" ? "import failed" : "preparing analysis"}</span><span>{repo.file_count ? `${repo.file_count} files` : repo.status === "ready" ? "analysis ready" : "indexing soon"}</span></div>{repo.error && <p className="repo-error">{repo.error}</p>}</Link>)}</div>}
    </section>

    <section className="capability-grid">
      <article className="panel-card"><p className="card-kicker">PRODUCT SHELL</p><h3>Dedicated repository detail pages.</h3><p>The dashboard now routes into a repository workspace instead of trying to do everything on one screen.</p></article>
      <article className="panel-card"><p className="card-kicker">LIVE STATE</p><h3>Automatic status refresh.</h3><p>Repository cards update from the API on an interval so queue state does not get stuck until a full browser refresh.</p></article>
      <article className="panel-card"><p className="card-kicker">NEXT SURFACES</p><h3>Planning, review, and health are next.</h3><p>This slice lays the foundation for the rest of the PRD instead of pretending those workflows already work.</p></article>
    </section>

    <footer className="workspace-footer"><span>veridexs / understand deeply</span><span>Phase 01 · Repository intelligence</span></footer>
  </main>;
}
