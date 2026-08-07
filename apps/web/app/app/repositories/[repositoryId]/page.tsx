"use client";

import { useState } from "react";
import { EmptyState } from "../../../../components/EmptyState";
import { useRepository } from "../../../../components/RepositoryProvider";
import { StatusBadge } from "../../../../components/StatusBadge";
import { api } from "../../../../lib/api";

export default function OverviewPage() {
  const { repository, intelligence, loading, isReady, refresh } = useRepository();
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");

  async function handleRetry() {
    if (!repository) return;
    setRetrying(true);
    setRetryError("");
    try {
      await api.retryImport(repository.id);
      await refresh();
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setRetrying(false);
    }
  }

  if (loading && !repository) {
    return <p className="loading-line">Loading repository overview…</p>;
  }

  if (!repository) {
    return <EmptyState title="Repository not found" detail="It may have been removed or you no longer have access." />;
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Understand</p>
          <h1>Overview</h1>
          <p className="page-lede">Import status, branch, and a short read of what this repository is.</p>
        </div>
        <StatusBadge status={repository.status} />
      </div>

      <section className="panel">
        <h2>Summary</h2>
        {isReady && intelligence ? (
          <p className="muted" style={{ margin: 0, whiteSpace: "pre-wrap" }}>{intelligence.summary}</p>
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            {repository.status === "failed"
              ? "Import failed — retry to generate a summary."
              : "Repository indexing in progress…"}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>Details</h2>
        <div className="kv-row"><span>State</span><strong>{repository.status}</strong></div>
        <div className="kv-row"><span>Branch</span><strong>{repository.branch ?? "Default"}</strong></div>
        <div className="kv-row"><span>Files</span><strong>{repository.file_count}</strong></div>
        <div className="kv-row">
          <span>URL</span>
          <strong style={{ fontSize: "0.85rem", wordBreak: "break-all", fontWeight: 400 }}>
            <a className="link-accent" href={repository.url} target="_blank" rel="noreferrer">
              {repository.url.replace("https://github.com/", "")}
            </a>
          </strong>
        </div>
        {repository.error ? <p className="error-text">{repository.error}</p> : null}
        {repository.status === "failed" ? (
          <div style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary btn-sm" type="button" onClick={() => void handleRetry()} disabled={retrying}>
              {retrying ? "Retrying…" : "Retry import"}
            </button>
            {retryError ? <p className="error-text">{retryError}</p> : null}
          </div>
        ) : null}
        {!isReady && repository.status !== "failed" ? (
          <p className="muted" style={{ marginTop: "1rem", marginBottom: 0 }}>
            Import in progress. This page refreshes automatically.
          </p>
        ) : null}
      </section>
    </div>
  );
}
