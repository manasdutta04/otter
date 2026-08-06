"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

type TabName = "overview" | "intelligence" | "chat" | "planner" | "memory" | "health" | "review" | "settings";
type RepoStatus = "queued" | "cloning" | "ready" | "failed";
type Repository = {
  id: string;
  name: string;
  url: string;
  status: RepoStatus;
  file_count: number;
  created_at: string;
  branch?: string | null;
  error?: string | null;
};
type Intelligence = {
  summary: string;
  tech_stack: string[];
  folders: string[];
  entry_points: string[];
  architecture_signals: string[];
};
type PlanResult = {
  title: string;
  complexity: string;
  steps: string[];
  affected_files: string[];
};
type HealthResult = {
  repository_id: string;
  architecture_score: number;
  security_score: number;
  maintainability_score: number;
  performance_score: number;
  debt_score: number;
  documentation_score: number;
  dependency_score: number;
  complexity_score: number;
  findings: string[];
  analyzed_at: string;
};
type ReviewFinding = {
  severity: string;
  category: string;
  title: string;
  file: string;
  line?: number;
};
type ReviewResult = {
  id: string;
  repository_id: string;
  findings: ReviewFinding[];
  created_at: string;
};
type MemoryResult = {
  overview?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_INTERVAL_MS = 5000;
const TABS: TabName[] = ["overview", "intelligence", "chat", "planner", "memory", "health", "review", "settings"];

export default function RepositoryDetailPage() {
  const params = useParams<{ repositoryId: string | string[] }>();
  const repositoryId = Array.isArray(params.repositoryId)
    ? params.repositoryId[0]
    : params.repositoryId;

  const [activeTab, setActiveTab] = useState<TabName>("overview");
  const [repository, setRepository] = useState<Repository | null>(null);
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const [planRequest, setPlanRequest] = useState("");
  const [planResult, setPlanResult] = useState<PlanResult | null>(null);
  const [planLoading, setPlanLoading] = useState(false);

  const [healthResult, setHealthResult] = useState<HealthResult | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [memoryResult, setMemoryResult] = useState<MemoryResult | null>(null);

  const isReady = repository?.status === "ready";

  const loadRepository = useCallback(async () => {
    if (!repositoryId) return;
    try {
      const repoRes = await fetch(`${API_URL}/repositories/${repositoryId}`, { credentials: "include" });
      if (repoRes.status === 401) { setAuthenticated(false); return; }
      if (!repoRes.ok) throw new Error("Unable to load repository");
      const repoData = (await repoRes.json()) as Repository;
      setRepository(repoData);
      setAuthenticated(true);
      const intelRes = await fetch(`${API_URL}/repositories/${repositoryId}/intelligence`, { credentials: "include" });
      if (intelRes.ok) setIntelligence((await intelRes.json()) as Intelligence);
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
      const data = (await res.json()) as { answer: string; sources: string[]; detail?: string };
      if (!res.ok) throw new Error(data.detail ?? "Chat failed");
      setAnswer(data.answer);
      setSources(data.sources ?? []);
    } catch (err) {
      setAnswer(err instanceof Error ? err.message : "Failed to get answer");
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
      const data = (await res.json()) as PlanResult & { detail?: string };
      if (!res.ok) throw new Error(data.detail ?? "Planning failed");
      setPlanResult(data);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Planning failed");
    } finally {
      setPlanLoading(false);
    }
  }

  async function fetchHealth() {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/health`, { credentials: "include" });
    if (res.ok) setHealthResult((await res.json()) as HealthResult);
  }

  async function fetchReview() {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/review`, { credentials: "include" });
    if (res.ok) setReviewResult((await res.json()) as ReviewResult);
  }

  async function fetchMemory() {
    const res = await fetch(`${API_URL}/repositories/${repositoryId}/memory`, { credentials: "include" });
    if (res.ok) setMemoryResult((await res.json()) as MemoryResult);
  }

  useEffect(() => {
    if (!isReady) return;
    if (activeTab === "health" && !healthResult) void fetchHealth();
    if (activeTab === "review" && !reviewResult) void fetchReview();
    if (activeTab === "memory" && !memoryResult) void fetchMemory();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isReady]);

  if (authenticated === false) {
    return (
      <main className="detail-shell">
        <div className="topbar">
          <Link className="brand" href="/">
            <span className="brand-mark">◈</span>
            <span>veridexs</span>
          </Link>
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
          <span className={`status-pill ${repository?.status ?? "queued"}`}>
            {repository?.status ?? "Loading"}
          </span>
          <span className="muted-topline">Workspace</span>
        </div>
      </header>

      <section className="detail-hero">
        <div>
          <p className="eyebrow">REPOSITORY WORKSPACE</p>
          <h1>{loading && !repository ? "Loading repository…" : repository?.name}</h1>
        </div>
        <div className="detail-actions">
          <Link className="ghost-button" href="/">Back to Dashboard</Link>
        </div>
      </section>

      {pageError && <p className="repo-error">{pageError}</p>}

      {/* Navigation Tabs */}
      <nav style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "4px",
        borderBottom: "1px solid #e2e8f0",
        marginBottom: "28px",
        marginTop: "8px",
      }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 18px",
              background: activeTab === tab ? "#1e293b" : "transparent",
              color: activeTab === tab ? "#ffffff" : "#64748b",
              border: "1px solid transparent",
              borderBottom: activeTab === tab ? "3px solid #2563eb" : "3px solid transparent",
              borderRadius: "6px 6px 0 0",
              cursor: "pointer",
              textTransform: "capitalize",
              fontWeight: activeTab === tab ? 700 : 500,
              fontSize: "13px",
              letterSpacing: "0.02em",
              transition: "background 0.15s, color 0.15s",
            }}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Overview */}
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

      {/* Intelligence */}
      {activeTab === "intelligence" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">REPOSITORY INTELLIGENCE</p>
          {intelligence ? (
            <div className="intelligence-layout">
              <div>
                <p className="card-kicker">TECH STACK</p>
                <div className="chip-list">
                  {intelligence.tech_stack.map((item) => <span className="chip" key={item}>{item}</span>)}
                </div>
                <p className="card-kicker">TOP FOLDERS</p>
                <div className="chip-list">
                  {intelligence.folders.slice(0, 10).map((item) => <span className="chip" key={item}>{item}</span>)}
                </div>
              </div>
              <div>
                <p className="card-kicker">ENTRY POINTS</p>
                <ul className="bullet-list">
                  {intelligence.entry_points.map((ep) => <li key={ep}>{ep}</li>)}
                </ul>
                <p className="card-kicker">SIGNALS</p>
                <ul className="bullet-list">
                  {intelligence.architecture_signals.map((sig) => <li key={sig}>{sig}</li>)}
                </ul>
              </div>
            </div>
          ) : <p className="muted">Intelligence is preparing...</p>}
        </section>
      )}

      {/* Chat */}
      {activeTab === "chat" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">GROUNDED SEMANTIC REPOSITORY CHAT</p>
          <form onSubmit={(e) => void askRepository(e)}>
            <div className="input-row">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a grounded question about repository source code..."
                required
                disabled={!isReady}
              />
              <button type="submit" disabled={chatLoading || !isReady}>
                {chatLoading ? "Searching..." : "Ask"}
              </button>
            </div>
          </form>
          {answer && (
            <div className="answer" style={{ marginTop: "20px" }}>
              <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>
            </div>
          )}
          {sources.length > 0 && (
            <div style={{ marginTop: "15px" }}>
              <p className="card-kicker">CITATIONS / SOURCE FILES</p>
              <div className="chip-list">
                {sources.map((s) => <span className="chip" key={s}>{s}</span>)}
              </div>
            </div>
          )}
          {!isReady && <p className="muted" style={{ marginTop: "12px" }}>Chat is enabled once the repository is ready.</p>}
        </section>
      )}

      {/* Planner */}
      {activeTab === "planner" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">AI IMPLEMENTATION PLANNER</p>
          <form onSubmit={(e) => void generatePlan(e)}>
            <div className="input-row">
              <input
                value={planRequest}
                onChange={(e) => setPlanRequest(e.target.value)}
                placeholder="Describe a feature or change, e.g. 'Add OAuth login'..."
                required
                disabled={!isReady}
              />
              <button type="submit" disabled={planLoading || !isReady}>
                {planLoading ? "Planning..." : "Generate Plan"}
              </button>
            </div>
          </form>
          {planResult && (
            <div className="answer" style={{ marginTop: "20px" }}>
              <h3>{planResult.title}</h3>
              <p><strong>Complexity:</strong> {planResult.complexity}</p>
              <p className="card-kicker">STEPS</p>
              <ul className="bullet-list">
                {planResult.steps.map((s, idx) => <li key={idx}>{s}</li>)}
              </ul>
              <p className="card-kicker">AFFECTED FILES</p>
              <div className="chip-list">
                {planResult.affected_files.map((f) => <span className="chip" key={f}>{f}</span>)}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Memory */}
      {activeTab === "memory" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">ENGINEERING MEMORY</p>
          <p className="muted">
            {memoryResult?.overview ?? "No architectural choices or memory notes logged yet."}
          </p>
        </section>
      )}

      {/* Health */}
      {activeTab === "health" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">REPOSITORY HEALTH SCORES</p>
          {healthResult ? (
            <div>
              <div className="status-stack" style={{ marginBottom: "20px" }}>
                <div className="status-row"><span>Architecture</span><strong>{healthResult.architecture_score}/100</strong></div>
                <div className="status-row"><span>Security</span><strong>{healthResult.security_score}/100</strong></div>
                <div className="status-row"><span>Maintainability</span><strong>{healthResult.maintainability_score}/100</strong></div>
                <div className="status-row"><span>Performance</span><strong>{healthResult.performance_score}/100</strong></div>
                <div className="status-row"><span>Technical Debt</span><strong>{healthResult.debt_score}/100</strong></div>
                <div className="status-row"><span>Documentation</span><strong>{healthResult.documentation_score}/100</strong></div>
                <div className="status-row"><span>Dependencies</span><strong>{healthResult.dependency_score}/100</strong></div>
                <div className="status-row"><span>Complexity</span><strong>{healthResult.complexity_score}/100</strong></div>
              </div>
              {(healthResult.findings ?? []).length > 0 && (
                <>
                  <p className="card-kicker">FINDINGS</p>
                  <ul className="bullet-list">
                    {healthResult.findings.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </>
              )}
            </div>
          ) : <p className="muted">Fetching repository health...</p>}
        </section>
      )}

      {/* Review */}
      {activeTab === "review" && (
        <section className="panel-card wide-panel">
          <p className="card-kicker">CODE QUALITY &amp; REVIEW</p>
          {reviewResult ? (
            <div>
              <p className="muted">
                {(reviewResult.findings ?? []).length === 0
                  ? "No review findings detected."
                  : `Found ${reviewResult.findings.length} issue${reviewResult.findings.length === 1 ? "" : "s"}.`}
              </p>
              {(reviewResult.findings ?? []).length > 0 && (
                <>
                  <p className="card-kicker">DETECTED ISSUES</p>
                  <ul className="bullet-list">
                    {(reviewResult.findings ?? []).map((iss, i) => (
                      <li key={i}>
                        <strong>[{iss.severity}] {iss.category}:</strong> {iss.title} ({iss.file}{iss.line != null ? `:${iss.line}` : ""})
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          ) : <p className="muted">Running code review scan...</p>}
        </section>
      )}

      {/* Settings */}
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