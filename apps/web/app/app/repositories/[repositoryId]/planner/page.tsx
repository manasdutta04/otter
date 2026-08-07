"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type Plan } from "../../../../../lib/api";

export default function PlannerPage() {
  const { repositoryId, isReady, getTabCache, setTabCache } = useRepository();
  const [request, setRequest] = useState("");
  const cached = getTabCache<Plan[]>("plans");
  const [plans, setPlans] = useState<Plan[]>(cached ?? []);
  const [loading, setLoading] = useState(!cached);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Plan | null>(null);

  const loadPlans = useCallback(async (opts?: { force?: boolean }) => {
    if (!isReady) {
      setLoading(false);
      return;
    }
    if (!opts?.force) {
      const existing = getTabCache<Plan[]>("plans");
      if (existing) {
        setPlans(existing);
        setLoading(false);
        return;
      }
    }
    setLoading(true);
    try {
      const data = await api.listPlans(repositoryId);
      setTabCache("plans", data);
      setPlans(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plans");
    } finally {
      setLoading(false);
    }
  }, [isReady, repositoryId, getTabCache, setTabCache]);

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  async function createPlan(event: FormEvent) {
    event.preventDefault();
    if (!request.trim()) return;
    setCreating(true);
    setError("");
    try {
      const plan = await api.createPlan(repositoryId, request.trim());
      setSelected(plan);
      setRequest("");
      await loadPlans({ force: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Planning failed");
    } finally {
      setCreating(false);
    }
  }

  if (!isReady) {
    return (
      <EmptyState
        title="Planner waits for a ready repo"
        detail="Generate implementation plans once Otter has finished importing the repository."
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Planner</h1>
          <p className="page-lede">Turn a goal into ordered steps before you generate code.</p>
        </div>
      </div>

      <section className="panel">
        <h2>Create a plan</h2>
        <form className="form-stack" onSubmit={(e) => void createPlan(e)}>
          <div className="field">
            <label htmlFor="plan-req">Change request</label>
            <textarea
              id="plan-req"
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              placeholder="Add OAuth login with GitHub…"
              required
              minLength={8}
              disabled={creating}
            />
          </div>
          <div>
            <button className="btn btn-primary" type="submit" disabled={creating}>
              {creating ? "Planning…" : "Generate plan"}
            </button>
          </div>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      {selected ? (
        <section className="panel">
          <h2>{selected.title}</h2>
          <p className="muted">Complexity: {selected.complexity}</p>
          <p style={{ whiteSpace: "pre-wrap" }}>{selected.summary}</p>
          <h3>Steps</h3>
          <ul className="bullet-list">
            {selected.steps.map((step, idx) => (
              <li key={`${idx}-${step}`}>{step}</li>
            ))}
          </ul>
          <h3>Affected files</h3>
          {selected.affected_files.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>None listed</p>
          ) : (
            <ul className="plain-list">
              {selected.affected_files.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
          {selected.risks.length > 0 ? (
            <>
              <h3>Risks</h3>
              <ul className="bullet-list">
                {selected.risks.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}

      <section className="panel">
        <h2>History</h2>
        {loading ? (
          <p className="loading-line">Loading plans…</p>
        ) : plans.length === 0 ? (
          <EmptyState title="No plans yet" detail="Create your first plan above." />
        ) : (
          plans.map((plan) => (
            <button
              key={plan.id}
              type="button"
              className="history-item"
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                background: "transparent",
                border: 0,
                color: "inherit",
                padding: "1rem 0",
                cursor: "pointer",
                borderBottom: "1px solid var(--line)",
              }}
              onClick={() => setSelected(plan)}
            >
              <strong>{plan.title}</strong>
              <div className="muted" style={{ fontSize: "0.82rem", marginTop: "0.25rem" }}>
                {plan.complexity} · {new Date(plan.created_at).toLocaleString()}
              </div>
            </button>
          ))
        )}
      </section>
    </div>
  );
}
