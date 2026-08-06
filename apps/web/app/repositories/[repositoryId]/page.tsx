"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

type Repository = { id: string; name: string; url: string; status: "queued" | "cloning" | "ready" | "failed"; file_count: number; created_at: string; branch?: string | null; error?: string | null };
type Intelligence = { summary: string; tech_stack: string[]; folders: string[]; entry_points: string[]; architecture_signals: string[] };
type ImportStatus = { job_id: string; repository_id: string; status: "queued" | "running" | "succeeded" | "failed"; attempt_count: number; error?: string | null; created_at: string; started_at?: string | null; finished_at?: string | null };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_INTERVAL_MS = 5000;

export default function RepositoryDetailPage() {
  const params = useParams<{ repositoryId: string | string[] }>();
  const repositoryId = Array.isArray(params.repositoryId) ? params.repositoryId[0] : params.repositoryId;
  
  const [activeTab, setActiveTab] = useState<"overview" | "intelligence" | "chat" | "planner" | "memory" | "health" | "review" | "settings">("overview");
  const [repository, setRepository] = useState<Repository | null>(null);
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null);
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  // Tab dynamic state
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const [planRequest, setPlanRequest] = useState("");
  const [planResult, setPlanResult] = useState<any>(null);
  const [planLoading, setPlanLoading] = useState(false);

  const [healthResult, setHealthResult] = useState<any>(null);
  const [reviewResult, setReviewResult] = useState<any>(null);
  const [memoryResult, setMemoryResult] = useState<any>(null);

  const isReady = repository?.status === "ready";

  const loadRepository = useCallback(async () => {
    if (!repositoryId) return;

    try {
      const repositoryResponse = await fetch(`${API_URL}/repositories/${repositoryId}`, { credentials: "include" });
      if (repositoryResponse.status === 401) {
        setAuthenticated(false);
        return;
      }
      if (!repositoryResponse.ok) throw new Error("Unable to load repository");

      const repositoryData = (await repositoryResponse.json()) as Repository;
      setRepository(repositoryData);
      setAuthenticated(true);

      const [importRes, intelRes] = await Promise.all([
        fetch(`${API_URL}/repositories/${repositoryId}/import-status`, { credentials: "include" }),
        fetch(`${API_URL}/repositories/${repositoryId}/intelligence`, { credentials: "include" }),
      ]);

      if (importRes.ok) setImportStatus(await importRes.json());
      if (intelRes.ok) setIntelligence(await intelRes.json());
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Error loading repository workspace.");
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    void loadRepository();
    const interval = window.setInterval(() => void loadRepository(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadRepository]);

  // Tab action handlers
  async function askRepository(e: FormEvent) {
    e.preventDefault();
    if (!repositoryId || !question.trim()) return;
    setChatLoading(true);
    try {
      const res = await fetch(`${API_URL}/repositories/${repositoryId}/chat`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Chat failed");
      setAnswer(data.answer);
      setSources(data.sources ?? []);
    } catch (err: any) {
      setAnswer(err.message || "Failed to get answer");
    } finally {
      setChatLoading(false);
    }
  }

  async function generatePlan(e: FormEvent) {
    e.preventDefault();
    if (!repositoryId || !planRequest.trim()) return;
    setPlanLoading(true);
    try {
      const res = await fetch(`${API_URL}/repositories/${repositoryId}/plans`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request: planRequest }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Planning failed");
      setPlanResult(data);
    } catch (err: any) {
      setPageError(err.message);
    } finally {
      setPlanLoading(false);
    }
  }

  const fetchHealth = async () => {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/health`, { credentials: "include" });
    if (res.ok) setHealthResult(await res.json());
  };

  const fetchReview = async () => {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/review`, { credentials: "include" });
    if (res.ok) setReviewResult(await res.json());
  };

  const fetchMemory = async () => {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/memory`, { credentials: "include" });
    if (res.ok) setMemoryResult(await res.json());
  };

  useEffect(() => {
    if (!isReady) return;
    if (activeTab === "health" && !healthResult) void fetchHealth();
    if (activeTab === "review" && !reviewResult) void fetchReview();
    if (activeTab === "memory" && !memoryResult) void fetchMemory();
  }, [activeTab, isReady]);

  if (authenticated === false) {
    return (
      <main className="detail-shell">
        <div className="topbar">
          <Link className="brand" href="/"><span className="brand-mark">◈</span><span>veridexs</span></Link>
        </div>
        <section className="empty-state">
          <p>Please connect GitHub to access workspace.</p>
          <a className="login-link" href={`${API_URL}/auth/github/login`}>Connect GitHub ↗</a>
        </section>
      </main>
    );
  }

  return (
    <main className="detail-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">◈</span>
          <span>veridexs</span>
        </Link>
        <div className="topbar-links">
          <span className={`status-pill ${repository?.status ?? "queued"}`}>{repository?.status ?? "Loading"}</span>
          <span className="muted-topline">Workspace</span>
        </div>
      </header>

      <section className="detail-hero">
        <div>
          <p className="eyebrow">REPOSITORY WORKSPACE</p>
          <h1>{repository?.name ?? "Loading repository…"}</h1>
        </div>
        <div className="detail-actions">
          <Link className="ghost-button" href="/">Back to Dashboard</Link>
        </div>
      </section>

      {/* Workspace Navigation Bar */}
      <nav className="workspace-tabs" style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255,255,255,0.1)", marginBottom: "20px" }}>
        {(["overview", "intelligence", "chat", "planner", "memory", "health", "review", "settings"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 16px",
              background: activeTab === tab ? "rgba(255,255,255,0.1)" : "transparent",
              color: activeTab === tab ? "#fff" : "rgba(255,255,255,0.6)",
              border: "none",
              borderBottom: activeTab === tab ? "2px solid #3b82f6" : "none",
              cursor: "pointer",
              textTransform: "capitalize",
              fontWeight: 500
            }}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Tab Content Views */}
      {activeTab === "overview" && (
        <section className="detail-grid">
          <article className="panel-card">
            <p className="card-kicker">STATUS</p>
            <div className="status-stack">
              <div className="status-row"><span>Status</span><strong>{repository?.status}</strong></div>
              <div className="status-row"><span>Branch</span><strong>{repository?.branch ?? "Default"}</strong></div>
              <div className="status-row"><span>Files</span><strong>{repository?.file_count ?? 0}</strong></div>
            </div>
          </article>
          <article className="panel-card wide-panel">
            <p className="card-kicker">SUMMARY</p>
            <p className="muted">{intelligence?.summary ?? "Repository indexing in progress..."}</p>
          </article>
        </section>
      )}

      {activeTab === "intelligence" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">REPOSITORY INTELLIGENCE</p>
          {intelligence ? (
            <div className="intelligence-layout">
              <div>
                <p className="card-kicker">TECH STACK</p>
                <div className="chip-list">{intelligence.tech_stack.map((item) => <span className="chip" key={item}>{item}</span>)}</div>
                <p className="card-kicker">TOP FOLDERS</p>
                <div className="chip-list">{intelligence.folders.slice(0, 10).map((item) => <span className="chip" key={item}>{item}</span>)}</div>
              </div>
              <div>
                <p className="card-kicker">ENTRY POINTS</p>
                <ul className="bullet-list">{intelligence.entry_points.map((ep) => <li key={ep}>{ep}</li>)}</ul>
                <p className="card-kicker">SIGNALS</p>
                <ul className="bullet-list">{intelligence.architecture_signals.map((sig) => <li key={sig}>{sig}</li>)}</ul>
              </div>
            </div>
          ) : <p className="muted">Intelligence is preparing...</p>}
        </section>
      )}

      {activeTab === "chat" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">GROUNDED SEMANTIC REPOSITORY CHAT</p>
          <form onSubmit={askRepository}>
            <div className="input-row">
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask grounded question about repository source code..." required disabled={!isReady} />
              <button disabled={chatLoading || !isReady}>{chatLoading ? "Searching..." : "Ask"}</button>
            </div>
          </form>
          {answer && (
            <div className="answer" style={{ marginTop: "20px" }}>
              <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>
            </div>
          )}
          {sources.length > 0 && (
            <div className="source-list" style={{ marginTop: "15px" }}>
              <p className="card-kicker">CITATIONS / SOURCE FILES</p>
              <div className="chip-list">{sources.map((s) => <span className="chip" key={s}>{s}</span>)}</div>
            </div>
          )}
        </section>
      )}

      {activeTab === "planner" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">AI IMPLEMENTATION PLANNER</p>
          <form onSubmit={generatePlan}>
            <div className="input-row">
              <input value={planRequest} onChange={(e) => setPlanRequest(e.target.value)} placeholder="Describe a feature or change e.g., 'Add OAuth login'..." required disabled={!isReady} />
              <button disabled={planLoading || !isReady}>{planLoading ? "Planning..." : "Generate Plan"}</button>
            </div>
          </form>
          {planResult && (
            <div className="answer" style={{ marginTop: "20px" }}>
              <h3>{planResult.title}</h3>
              <p><strong>Complexity:</strong> {planResult.complexity}</p>
              <p className="card-kicker">STEPS</p>
              <ul className="bullet-list">{planResult.steps.map((s: string, idx: number) => <li key={idx}>{s}</li>)}</ul>
              <p className="card-kicker">AFFECTED FILES</p>
              <div className="chip-list">{planResult.affected_files.map((f: string) => <span className="chip" key={f}>{f}</span>)}</div>
            </div>
          )}
        </section>
      )}

      {activeTab === "memory" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">ENGINEERING MEMORY</p>
          <p className="muted">{memoryResult?.overview ?? "No architectural choices or memory notes logged yet."}</p>
        </section>
      )}

      {activeTab === "health" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">REPOSITORY HEALTH SCORE</p>
          {healthResult ? (
            <div>
              <h2>Status: {healthResult.status} (Score: {healthResult.score}/100)</h2>
              <p className="card-kicker">RECOMMENDATIONS</p>
              <ul className="bullet-list">{healthResult.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul>
            </div>
          ) : <p className="muted">Fetching repository health...</p>}
        </section>
      )}

      {activeTab === "review" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">CODE QUALITY & REVIEW</p>
          {reviewResult ? (
            <div>
              <p className="muted">{reviewResult.summary}</p>
              <p className="card-kicker">DETECTED ISSUES</p>
              <ul className="bullet-list">
                {reviewResult.issues.map((iss: any, i: number) => (
                  <li key={i}><strong>[{iss.severity}] {iss.category}:</strong> {iss.title} ({iss.file})</li>
                ))}
              </ul>
            </div>
          ) : <p className="muted">Running code review scan...</p>}
        </section>
      )}

      {activeTab === "settings" && (
        <section className="panel-card">
          <p className="card-kicker">SETTINGS</p>
          <p className="muted">Repository ID: {repositoryId}</p>
          <p className="muted">Source URL: {repository?.url}</p>
        </section>
      )}
    </main>
  );
}