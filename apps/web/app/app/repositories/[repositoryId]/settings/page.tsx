"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { StatusBadge } from "../../../../../components/StatusBadge";
import {
  api,
  type ArchitectureAnalysis,
  type Document,
  type PerformanceReport,
} from "../../../../../lib/api";

export default function SettingsPage() {
  const { repositoryId, repository, isReady, loading: repoLoading } = useRepository();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [architecture, setArchitecture] = useState<ArchitectureAnalysis | null>(null);
  const [performance, setPerformance] = useState<PerformanceReport | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [loadingExtra, setLoadingExtra] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = useCallback(async () => {
    if (!isReady) return;
    setLoadingDocs(true);
    try {
      const docs = await api.listDocuments(repositoryId);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoadingDocs(false);
    }
  }, [isReady, repositoryId]);

  const loadAnalyses = useCallback(async () => {
    if (!isReady) return;
    setLoadingExtra(true);
    try {
      const [arch, perf] = await Promise.all([
        api.getArchitectureAnalysis(repositoryId).catch(() => null),
        api.getPerformance(repositoryId).catch(() => null),
      ]);
      setArchitecture(arch);
      setPerformance(perf);
    } finally {
      setLoadingExtra(false);
    }
  }, [isReady, repositoryId]);

  useEffect(() => {
    void loadDocuments();
    void loadAnalyses();
  }, [loadDocuments, loadAnalyses]);

  async function generateOverview() {
    setGenerating(true);
    setError("");
    try {
      await api.generateOverview(repositoryId);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate overview");
    } finally {
      setGenerating(false);
    }
  }

  if (repoLoading && !repository) return <p className="loading-line">Loading settings…</p>;
  if (!repository) return <EmptyState title="Repository missing" detail="Unable to load repository metadata." />;

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Repository settings</h1>
        </div>
        <StatusBadge status={repository.status} />
      </div>

      <section className="panel">
        <h2>Metadata</h2>
        <div className="kv-row"><span>Name</span><strong>{repository.name}</strong></div>
        <div className="kv-row"><span>ID</span><strong style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>{repository.id}</strong></div>
        <div className="kv-row"><span>URL</span><strong style={{ fontSize: "0.85rem", wordBreak: "break-all" }}>{repository.url}</strong></div>
        <div className="kv-row"><span>Branch</span><strong>{repository.branch ?? "—"}</strong></div>
        <div className="kv-row"><span>Files</span><strong>{repository.file_count}</strong></div>
        <div className="kv-row"><span>Created</span><strong>{new Date(repository.created_at).toLocaleString()}</strong></div>
      </section>

      {!isReady ? (
        <EmptyState
          title="Docs & analysis locked"
          detail="Document generation and architecture/performance summaries unlock when the repository is ready."
        />
      ) : (
        <>
          <section className="panel">
            <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>Generated documents</h2>
              <button className="btn btn-primary btn-sm" type="button" onClick={() => void generateOverview()} disabled={generating}>
                {generating ? "Generating…" : "Generate overview"}
              </button>
            </div>
            {error ? <p className="error-text">{error}</p> : null}
            {loadingDocs ? (
              <p className="loading-line">Loading documents…</p>
            ) : documents.length === 0 ? (
              <p className="muted">No documents yet. Generate an overview to create one.</p>
            ) : (
              documents.map((doc) => (
                <article className="history-item" key={doc.id}>
                  <div className="chip-list" style={{ marginBottom: "0.35rem" }}>
                    <span className="chip">{doc.kind}</span>
                  </div>
                  <strong>{doc.title}</strong>
                  <p className="muted" style={{ whiteSpace: "pre-wrap" }}>{doc.content}</p>
                  <div className="muted" style={{ fontSize: "0.75rem" }}>{new Date(doc.created_at).toLocaleString()}</div>
                </article>
              ))
            )}
          </section>

          <div className="grid-2">
            <section className="panel">
              <h2>Architecture analysis</h2>
              {loadingExtra && !architecture ? (
                <p className="loading-line">Loading…</p>
              ) : architecture ? (
                <>
                  <div className="score-cell" style={{ marginBottom: "0.85rem" }}>
                    <span>Score</span>
                    <strong>{architecture.score}</strong>
                  </div>
                  {(architecture.findings ?? []).length === 0 ? (
                    <p className="muted">No architecture findings.</p>
                  ) : (
                    <ul className="bullet-list">
                      {architecture.findings.map((finding, idx) => (
                        <li key={idx}>
                          {typeof finding.title === "string" ? finding.title : "Finding"}
                          {typeof finding.detail === "string" ? ` — ${finding.detail}` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : (
                <p className="muted">No architecture analysis available.</p>
              )}
            </section>

            <section className="panel">
              <h2>Performance</h2>
              {loadingExtra && !performance ? (
                <p className="loading-line">Loading…</p>
              ) : performance ? (
                <>
                  <div className="score-cell" style={{ marginBottom: "0.85rem" }}>
                    <span>Score</span>
                    <strong>{performance.score}</strong>
                  </div>
                  {(performance.hotspots ?? []).length === 0 ? (
                    <p className="muted">No hotspots reported.</p>
                  ) : (
                    <ul className="bullet-list">
                      {performance.hotspots.map((hotspot, idx) => (
                        <li key={idx}>
                          {typeof hotspot.path === "string"
                            ? hotspot.path
                            : typeof hotspot.title === "string"
                              ? hotspot.title
                              : JSON.stringify(hotspot)}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : (
                <p className="muted">No performance report available.</p>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
