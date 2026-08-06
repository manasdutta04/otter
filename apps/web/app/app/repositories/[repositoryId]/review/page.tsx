"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type ReviewResult } from "../../../../../lib/api";

export default function ReviewPage() {
  const { repositoryId, isReady, getTabCache, setTabCache } = useRepository();
  const cached = getTabCache<ReviewResult>("review");
  const [review, setReview] = useState<ReviewResult | null>(cached ?? null);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isReady) {
      setLoading(false);
      return;
    }
    const existing = getTabCache<ReviewResult>("review");
    if (existing) {
      setReview(existing);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void api
      .getReview(repositoryId)
      .then((data) => {
        if (!cancelled) {
          setTabCache("review", data);
          setReview(data);
          setError("");
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load review");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isReady, repositoryId, getTabCache, setTabCache]);

  if (!isReady) {
    return (
      <EmptyState
        title="Review unavailable"
        detail="Code quality review runs after the repository is ready."
      />
    );
  }

  if (loading) return <p className="loading-line">Running review scan…</p>;
  if (error) return <EmptyState title="Couldn’t load review" detail={error} />;
  if (!review) return <EmptyState title="No review yet" detail="No review report is available." />;

  const findings = review.findings ?? [];

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Review</p>
          <h1>Code quality findings</h1>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            {findings.length === 0
              ? "No findings detected."
              : `${findings.length} finding${findings.length === 1 ? "" : "s"} · ${new Date(review.created_at).toLocaleString()}`}
          </p>
        </div>
      </div>

      <section className="panel">
        {findings.length === 0 ? (
          <EmptyState title="Clean scan" detail="No review findings were detected in this repository." />
        ) : (
          findings.map((finding, idx) => (
            <div className="finding-row" key={`${finding.file}-${finding.line}-${idx}`}>
              <div className="chip-list">
                <span className="chip">{finding.severity}</span>
                <span className="chip">{finding.category}</span>
              </div>
              <strong>{finding.title}</strong>
              <span className="muted" style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                {finding.file}:{finding.line}
              </span>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
