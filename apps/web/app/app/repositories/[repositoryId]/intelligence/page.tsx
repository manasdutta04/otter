"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type FolderIntelligence, type Intelligence } from "../../../../../lib/api";

function folderLabel(item: FolderIntelligence | string): FolderIntelligence {
  if (typeof item === "string") {
    return { path: item, role: "source", file_count: 0 };
  }
  return item;
}

export default function IntelligencePage() {
  const { repositoryId, isReady, intelligence: sharedIntel, loading: repoLoading } = useRepository();
  const [intelligence, setIntelligence] = useState<Intelligence | null>(sharedIntel);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setIntelligence(sharedIntel);
  }, [sharedIntel]);

  useEffect(() => {
    if (!isReady) return;
    let cancelled = false;
    setLoading(true);
    void api
      .getIntelligence(repositoryId)
      .then((data) => {
        if (!cancelled) {
          setIntelligence(data);
          setError("");
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load intelligence");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isReady, repositoryId]);

  if (repoLoading) return <p className="loading-line">Loading…</p>;

  if (!isReady) {
    return (
      <EmptyState
        title="Intelligence unavailable"
        detail="Repository intelligence appears once the import finishes and status is ready."
      />
    );
  }

  if (loading && !intelligence) return <p className="loading-line">Analyzing repository…</p>;
  if (error && !intelligence) return <EmptyState title="Couldn’t load intelligence" detail={error} />;
  if (!intelligence) return <EmptyState title="No intelligence yet" detail="Analysis has not produced a report for this repository." />;

  const analysis = intelligence.analysis;
  const folders = intelligence.folders.map(folderLabel);

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Intelligence</p>
          <h1>How this codebase is shaped</h1>
        </div>
      </div>

      <section className="panel">
        <h2>Summary</h2>
        <p className="muted" style={{ margin: 0, whiteSpace: "pre-wrap" }}>{intelligence.summary}</p>
        {analysis?.summary_facts?.length ? (
          <ul className="bullet-list" style={{ marginTop: "0.75rem" }}>
            {analysis.summary_facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="panel">
        <h2>Tech stack</h2>
        {intelligence.tech_stack.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>None detected</p>
        ) : (
          <p style={{ margin: 0, color: "var(--ink-soft)" }}>
            {intelligence.tech_stack.join(" · ")}
          </p>
        )}
        {analysis?.frameworks?.length ? (
          <p className="muted" style={{ margin: "0.55rem 0 0" }}>
            Frameworks: {analysis.frameworks.join(" · ")}
          </p>
        ) : null}
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Folders</h2>
          {folders.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>None detected</p>
          ) : (
            <ul className="plain-list">
              {folders.slice(0, 14).map((item) => (
                <li key={item.path}>
                  <strong>{item.path}</strong>
                  <span className="muted"> — {item.role}{item.file_count ? ` (${item.file_count})` : ""}</span>
                  {item.explanation ? (
                    <div className="muted" style={{ fontSize: "0.9rem", marginTop: "0.2rem" }}>{item.explanation}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <h2>Entry points</h2>
          {intelligence.entry_points.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>None detected</p>
          ) : (
            <ul className="plain-list">
              {intelligence.entry_points.map((ep) => (
                <li key={ep}>{ep}</li>
              ))}
            </ul>
          )}
          <h3 style={{ marginTop: "1.5rem" }}>Architecture signals</h3>
          {intelligence.architecture_signals.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>None detected</p>
          ) : (
            <ul className="bullet-list">
              {intelligence.architecture_signals.map((sig) => (
                <li key={sig}>{sig}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {analysis?.api_routes?.length ? (
        <section className="panel">
          <h2>API routes</h2>
          <ul className="plain-list">
            {analysis.api_routes.slice(0, 20).map((route) => (
              <li key={`${route.method}:${route.path}:${route.file}`}>
                <code>{route.method}</code> {route.path}
                <span className="muted"> — {route.file}{route.line ? `:${route.line}` : ""}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="grid-2">
        {analysis?.databases?.length ? (
          <section className="panel">
            <h2>Databases / ORM</h2>
            <ul className="bullet-list">
              {analysis.databases.map((db) => (
                <li key={db.orm}>
                  <strong>{db.orm}</strong> — {db.evidence}
                  {db.files?.length ? (
                    <div className="muted" style={{ fontSize: "0.85rem" }}>{db.files.slice(0, 4).join(" · ")}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {analysis?.auth?.length ? (
          <section className="panel">
            <h2>Authentication</h2>
            <ul className="bullet-list">
              {analysis.auth.map((item) => (
                <li key={item.mechanism}>
                  <strong>{item.mechanism}</strong>
                  {item.notes ? <span className="muted"> — {item.notes}</span> : null}
                  {item.files?.length ? (
                    <div className="muted" style={{ fontSize: "0.85rem" }}>{item.files.slice(0, 4).join(" · ")}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      {(analysis?.config_files?.length || analysis?.testing?.length || analysis?.docker?.length) ? (
        <section className="panel">
          <h2>Config · tests · docker</h2>
          {analysis?.testing?.length ? (
            <p className="muted" style={{ margin: "0 0 0.5rem" }}>Testing: {analysis.testing.join(" · ")}</p>
          ) : null}
          {analysis?.docker?.length ? (
            <p className="muted" style={{ margin: "0 0 0.5rem" }}>Docker: {analysis.docker.join(" · ")}</p>
          ) : null}
          {analysis?.config_files?.length ? (
            <ul className="plain-list">
              {analysis.config_files.slice(0, 12).map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
