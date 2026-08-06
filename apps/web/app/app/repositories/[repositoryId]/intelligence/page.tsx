"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type Intelligence } from "../../../../../lib/api";

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
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Top folders</h2>
          {intelligence.folders.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>None detected</p>
          ) : (
            <ul className="plain-list">
              {intelligence.folders.slice(0, 12).map((item) => (
                <li key={item}>{item}</li>
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
    </div>
  );
}
