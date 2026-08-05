"use client";

import { FormEvent, useEffect, useState } from "react";

type Repository = { id: string; name: string; url: string; status: string; file_count: number; branch?: string; error?: string };
type Intelligence = { summary: string; tech_stack: string[]; folders: string[]; entry_points: string[]; architecture_signals: string[] };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Dashboard() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selected, setSelected] = useState<Repository | null>(null);
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [url, setUrl] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState("");

  async function loadRepositories() {
    const response = await fetch(`${API_URL}/repositories`, { credentials: "include" });
    if (response.ok) setRepositories((await response.json()).repositories);
  }
  async function loadSession() {
    const response = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
    if (response.ok && (await response.json()).authenticated) { setAuthenticated(true); await loadRepositories(); }
  }
  useEffect(() => { loadSession(); }, []);

  async function selectRepository(repository: Repository) {
    setSelected(repository); setIntelligence(null); setAnswer("");
    const response = await fetch(`${API_URL}/repositories/${repository.id}/intelligence`, { credentials: "include" });
    if (response.ok) setIntelligence(await response.json());
  }
  async function importRepository(event: FormEvent) {
    event.preventDefault(); setError("");
    const response = await fetch(`${API_URL}/repositories`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Import failed"); return; }
    setRepositories((current) => [data, ...current]); setUrl("");
  }
  async function askRepository(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    const response = await fetch(`${API_URL}/repositories/${selected.id}/chat`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
    const data = await response.json(); setAnswer(response.ok ? data.answer : data.detail); setQuestion("");
  }

  return <main className="shell">
    <nav className="topbar"><div className="brand"><span className="brand-mark">◈</span><span>veridexs</span></div><span className="github-link">{authenticated ? "GitHub connected ●" : <a href={`${API_URL}/auth/github/login`}>Connect GitHub ↗</a>}</span></nav>
    <section className="hero"><p className="eyebrow">ENGINEERING INTELLIGENCE / 01</p><h1>Your codebase,<br /><em>made legible.</em></h1><p className="intro">Import a repository and get the map before you make the move. veridexs turns unfamiliar systems into decisions you can act on.</p></section>
    {authenticated ? <section className="import-card"><div><p className="card-kicker">START WITH A REPOSITORY</p><h2>Bring a codebase into focus.</h2><p className="muted">Paste a GitHub URL. veridexs will clone, inspect, and prepare it for questions.</p></div><form onSubmit={importRepository}><label htmlFor="repo-url">GitHub repository URL</label><div className="input-row"><input id="repo-url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://github.com/owner/repository" required /><button>Import repository <span>→</span></button></div>{error && <p className="error">{error}</p>}</form></section> : <section className="import-card"><div><p className="card-kicker">CONNECT TO BEGIN</p><h2>Your workspace starts with GitHub.</h2><p className="muted">Connect GitHub to import repositories and understand the systems you work on.</p></div></section>}
    <section className="workspace"><div className="section-heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>Repositories</h2></div><span className="count">{String(repositories.length).padStart(2, "0")} tracked</span></div>{repositories.length === 0 ? <div className="empty"><span>◎</span><p>{authenticated ? "No repositories yet." : "Connect GitHub to see your workspace."}</p><small>Phase 01 combines import, repository intelligence, and contextual questions.</small></div> : <div className="repo-grid">{repositories.map((repo) => <article className={`repo-card ${selected?.id === repo.id ? "selected" : ""}`} key={repo.id} onClick={() => selectRepository(repo)}><div className="repo-icon">⌁</div><div className="repo-info"><h3>{repo.name}</h3><p>{repo.url.replace("https://github.com/", "")}</p></div><span className={`status ${repo.status}`}>{repo.status}</span><div className="repo-meta"><span>{repo.branch ? `branch / ${repo.branch}` : "preparing analysis"}</span><span>{repo.file_count ? `${repo.file_count} files` : "indexing soon"}</span></div></article>)}</div>}</section>
    {selected && <section className="insight-panel"><div className="section-heading"><div><p className="eyebrow">REPOSITORY READ</p><h2>{selected.name}</h2></div><span className="count">intelligence layer</span></div>{intelligence ? <div className="insight-grid"><div><p className="muted">{intelligence.summary}</p><p className="card-kicker">TECH STACK</p><div className="chips">{intelligence.tech_stack.map((item) => <span key={item}>{item}</span>)}</div></div><div><p className="card-kicker">ENTRY POINTS</p><ul>{intelligence.entry_points.slice(0, 8).map((item) => <li key={item}>{item}</li>)}</ul><p className="card-kicker">SIGNALS</p><ul>{intelligence.architecture_signals.map((item) => <li key={item}>{item}</li>)}</ul></div></div> : <p className="muted">Analysis is not ready yet. Refresh after the import worker finishes.</p>}<form className="chat-form" onSubmit={askRepository}><label htmlFor="question">ASK THE REPOSITORY</label><div className="input-row"><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Where is authentication implemented?" required /><button>Ask <span>→</span></button></div></form>{answer && <div className="answer"><span>veridexs / read</span><p>{answer}</p></div>}</section>}
    <footer><span>veridexs / understand deeply</span><span>Phase 01 · Repository intelligence</span></footer>
  </main>;
}
