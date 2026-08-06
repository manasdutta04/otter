"use client";

import { useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type HealthReport } from "../../../../../lib/api";

const SCORE_LABELS: { key: keyof HealthReport; label: string }[] = [
  { key: "architecture_score", label: "Architecture" },
  { key: "security_score", label: "Security" },
  { key: "maintainability_score", label: "Maintainability" },
  { key: "performance_score", label: "Performance" },
  { key: "debt_score", label: "Tech debt" },
  { key: "documentation_score", label: "Documentation" },
  { key: "dependency_score", label: "Dependencies" },
  { key: "complexity_score", label: "Complexity" },
];

export default function HealthPage() {
  const { repositoryId, isReady, getTabCache, setTabCache } = useRepository();
  const cached = getTabCache<HealthReport>("health");
  const [report, setReport] = useState<HealthReport | null>(cached ?? null);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isReady) {
      setLoading(false);
      return;
    }
    const existing = getTabCache<HealthReport>("health");
    if (existing) {
      setReport(existing);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void api
      .getHealth(repositoryId)
      .then((data) => {
        if (!cancelled) {
          setTabCache("health", data);
          setReport(data);
          setError("");
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load health");
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
        title="Health report pending"
        detail="Repository health scores are available after a successful import."
      />
    );
  }

  if (loading) return <p className="loading-line">Fetching repository health…</p>;
  if (error) return <EmptyState title="Couldn’t load health" detail={error} />;
  if (!report) return <EmptyState title="No health report" detail="No health analysis is available yet." />;

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Health</p>
          <h1>Repository health</h1>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Analyzed {new Date(report.analyzed_at).toLocaleString()}
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="score-grid">
          {SCORE_LABELS.map(({ key, label }) => (
            <div className="score-cell" key={key}>
              <span>{label}</span>
              <strong>{report[key] as number}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Findings</h2>
        {(report.findings ?? []).length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>No health findings.</p>
        ) : (
          <ul className="bullet-list">
            {report.findings.map((finding, idx) => (
              <li key={`${idx}-${finding}`}>{finding}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
