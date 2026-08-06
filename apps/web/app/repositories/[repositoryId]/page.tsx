"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

type Repository = { id: string; name: string; url: string; status: "queued" | "cloning" | "ready" | "failed"; file_count: number; created_at: string; branch?: string | null; error?: string | null };
type Intelligence = { summary: string; tech_stack: string[]; folders: string[]; entry_points: string[]; architecture_signals: string[] };
type ImportStatus = { job_id: string; repository_id: string; status: "queued" | "running" | "succeeded" | "failed"; attempt_count: number; error?: string | null; created_at: string; started_at?: string | null; finished_at?: string | null };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_INTERVAL_MS = 5000;

const STATUS_LABELS: Record<Repository["status"] | ImportStatus["status"], string> = {
  queued: "Queued",
  cloning: "Cloning",
  ready: "Ready",
  failed: "Failed",
  running: "Running",
  succeeded: "Succeeded",
};

function formatDate(value?: string | null): string {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export default function RepositoryDetailPage() {
  const params = useParams<{ repositoryId: string | string[] }>();
  const repositoryId = Array.isArray(params.repositoryId) ? params.repositoryId[0] : params.repositoryId;
  const [repository, setRepository] = useState<Repository | null>(null);
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null);
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [pageError, setPageError] = useState("");

  const isReady = repository?.status === "ready";

  const loadRepository = useCallback(async () => {
    if (!repositoryId) {
      setPageError("Repository id is missing from the route.");
      setLoading(false);
      return;
    }

    try {
      const repositoryResponse = await fetch(`${API_URL}/repositories/${repositoryId}`, { credentials: "include" });
      if (repositoryResponse.status === 401) {
        setAuthenticated(false);
        setRepository(null);
        return;
      }
      if (repositoryResponse.status === 404) {
        setPageError("Repository not found.");
        setRepository(null);
        return;
      }
      if (!repositoryResponse.ok) {
        throw new Error("Unable to load repository");
      }

      const repositoryData = (await repositoryResponse.json()) as Repository;
      setRepository(repositoryData);
      setAuthenticated(true);
      setPageError("");

      const [importStatusResponse, intelligenceResponse] = await Promise.all([
        fetch(`${API_URL}/repositories/${repositoryId}/import-status`, { credentials: "include" }),
        fetch(`${API_URL}/repositories/${repositoryId}/intelligence`, { credentials: "include" }),
      ]);

      if (importStatusResponse.ok) {
        setImportStatus((await importStatusResponse.json()) as ImportStatus);
      } else if (importStatusResponse.status === 404) {
        setImportStatus(null);
      }

      if (intelligenceResponse.ok) {
        setIntelligence((await intelligenceResponse.json()) as Intelligence);
      } else if (repositoryData.status !== "ready") {
        setIntelligence(null);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to load repository workspace.");
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    void loadRepository();
    const interval = window.setInterval(() => {
      void loadRepository();
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadRepository]);

  const statusRows = useMemo(() => [
    { label: "Repository", value: repository ? STATUS_LABELS[repository.status] : "Loading" },
    { label: "Import job", value: importStatus ? STATUS_LABELS[importStatus.status] : "Waiting" },
    { label: "Branch", value: repository?.branch ?? "Pending" },
    { label: "Files", value: repository?.file_count ? `${repository.file_count}` : "Analyzing" },
  ], [importStatus, repository]);

  async function retryImport() {
    if (!repositoryId) {
      return;
    }
    setRetrying(true);
    try {
      const response = await fetch(`${API_URL}/repositories/${repositoryId}/retry-import`, { method: "POST", credentials: "include" });
      if (!response.ok) {
        throw new Error("Retry import failed");
      }
      await loadRepository();
    } finally {
      setRetrying(false);
    }
  }

  async function askRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!repositoryId || !question.trim()) {
      return;
    }
    setChatLoading(true);
    try {
      const response = await fetch(`${API_URL}/repositories/${repositoryId}/chat`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "Chat request failed");
      }
      setAnswer(data.answer);
      setSources(data.sources ?? []);
      setQuestion("");
    } catch (error) {
      setAnswer(error instanceof Error ? error.message : "Unable to answer the question.");
      setSources([]);
    } finally {
      setChatLoading(false);
    }
  }

  if (authenticated === false) {
    return <main className="detail-shell"><div className="topbar"><Link className="brand" href="/"><span className="brand-mark">◈</span><span>veridexs</span></Link></div><section className="empty-state"><span>◎</span><p>You need to connect GitHub first.</p><small><a className="login-link" href={`${API_URL}/auth/github/login`}>Connect GitHub ↗</a></small></section></main>;
  }

  return <main className="detail-shell">
    <header className="topbar">
      <Link className="brand" href="/">
        <span className="brand-mark">◈</span>
        <span>veridexs</span>
      </Link>
      <div className="topbar-links">
        <span className={`status-pill ${repository?.status ?? "queued"}`}>{repository ? STATUS_LABELS[repository.status] : "Loading"}</span>
        <span className="muted-topline">Repository workspace</span>
      </div>
    </header>

    <section className="detail-hero">
      <div>
        <p className="eyebrow">REPOSITORY READ</p>
        <h1>{repository?.name ?? "Loading repository…"}</h1>
        <p className="intro">This workspace combines repository status, intelligence, and repository chat in one dedicated view.</p>
      </div>
      <div className="detail-actions">
        <Link className="ghost-button" href="/">Back to workspace</Link>
        {repository?.status === "failed" && <button type="button" onClick={() => void retryImport()} disabled={retrying}>{retrying ? "Retrying" : "Retry import"}</button>}
      </div>
    </section>

    <section className="detail-grid">
      <article className="panel-card">
        <p className="card-kicker">IMPORT STATE</p>
        <div className="status-stack">
          {statusRows.map((row) => <div className="status-row" key={row.label}><span>{row.label}</span><strong>{row.value}</strong></div>)}
        </div>
        <p className="repo-error">{repository?.error ?? importStatus?.error ?? ""}</p>
        <div className="timeline">
          <div className="timeline-item"><span>Created</span><strong>{formatDate(repository ? repository.created_at : importStatus?.created_at)}</strong></div>
          <div className="timeline-item"><span>Started</span><strong>{formatDate(importStatus?.started_at)}</strong></div>
          <div className="timeline-item"><span>Finished</span><strong>{formatDate(importStatus?.finished_at)}</strong></div>
          <div className="timeline-item"><span>Attempts</span><strong>{importStatus?.attempt_count ?? 0}</strong></div>
        </div>
      </article>

      <article className="panel-card wide-panel">
        <p className="card-kicker">INTELLIGENCE</p>
        {loading && !repository ? <p className="muted">Loading repository intelligence…</p> : intelligence ? <div className="intelligence-layout"><div><p className="muted">{intelligence.summary}</p><p className="card-kicker">TECH STACK</p><div className="chip-list">{intelligence.tech_stack.map((item) => <span className="chip" key={item}>{item}</span>)}</div><p className="card-kicker">FOLDERS</p><div className="chip-list">{intelligence.folders.slice(0, 10).map((item) => <span className="chip" key={item}>{item}</span>)}</div></div><div><p className="card-kicker">ENTRY POINTS</p><ul className="bullet-list">{intelligence.entry_points.slice(0, 8).map((item) => <li key={item}>{item}</li>)}</ul><p className="card-kicker">SIGNALS</p><ul className="bullet-list">{intelligence.architecture_signals.map((item) => <li key={item}>{item}</li>)}</ul></div></div> : <p className="muted">Analysis is not ready yet. The worker is still preparing the repository.</p>}
      </article>
    </section>

    <section className="detail-grid lower-grid">
      <article className="panel-card wide-panel">
        <p className="card-kicker">ASK THE REPOSITORY</p>
        <form onSubmit={askRepository}>
          <label htmlFor="repository-question">Question</label>
          <div className="input-row">
            <input id="repository-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Where is authentication implemented?" required disabled={chatLoading || !isReady} />
            <button disabled={chatLoading || !isReady}>{chatLoading ? "Asking" : "Ask"} <span>→</span></button>
          </div>
        </form>
        {answer && <div className="answer"><span>veridexs / read</span><p>{answer}</p></div>}
        {sources.length > 0 && <div className="source-list"><p className="card-kicker">SOURCES</p><div className="chip-list">{sources.map((source) => <span className="chip" key={source}>{source}</span>)}</div></div>}
        {!isReady && <p className="muted">Chat is enabled once the repository reaches the ready state.</p>}
      </article>

      <article className="panel-card">
        <p className="card-kicker">WORKSPACE STATUS</p>
        <p className="muted">Repository details and job status refresh automatically every few seconds so the queue state does not depend on a manual browser refresh.</p>
        {pageError && <p className="repo-error">{pageError}</p>}
      </article>
    </section>
  </main>;
}