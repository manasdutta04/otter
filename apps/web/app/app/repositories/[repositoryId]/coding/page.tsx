"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { StatusBadge } from "../../../../../components/StatusBadge";
import { api, type CodeTask, type PullRequestResult, type TestResult } from "../../../../../lib/api";

export default function CodingPage() {
  const { repositoryId, isReady } = useRepository();
  const [tasks, setTasks] = useState<CodeTask[]>([]);
  const [request, setRequest] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState<{ taskId: string; result: TestResult } | null>(null);
  const [prResult, setPrResult] = useState<{ taskId: string; result: PullRequestResult } | null>(null);
  const [prTitle, setPrTitle] = useState("");
  const [prBody, setPrBody] = useState("");
  const [prTaskId, setPrTaskId] = useState<string | null>(null);

  const loadTasks = useCallback(async () => {
    if (!isReady) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.listCodeTasks(repositoryId);
      setTasks(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load code tasks");
    } finally {
      setLoading(false);
    }
  }, [isReady, repositoryId]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setError("");
    try {
      await api.createCodeTask(repositoryId, request.trim());
      setRequest("");
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setCreating(false);
    }
  }

  async function runAction(taskId: string, action: () => Promise<unknown>) {
    setBusyId(taskId);
    setError("");
    try {
      await action();
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleTest(taskId: string) {
    setBusyId(taskId);
    setError("");
    try {
      const result = await api.testCodeTask(repositoryId, taskId);
      setTestResult({ taskId, result });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handlePr(event: FormEvent) {
    event.preventDefault();
    if (!prTaskId) return;
    setBusyId(prTaskId);
    setError("");
    try {
      const result = await api.createPullRequest(repositoryId, prTaskId, {
        title: prTitle.trim(),
        body: prBody.trim(),
      });
      setPrResult({ taskId: prTaskId, result });
      setPrTaskId(null);
      setPrTitle("");
      setPrBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pull request failed");
    } finally {
      setBusyId(null);
    }
  }

  if (!isReady) {
    return (
      <EmptyState
        title="Coding tasks need a ready repo"
        detail="Create and approve code changes after Otter finishes importing the repository."
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Coding</p>
          <h1>Code tasks</h1>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Generate patches, approve before apply, then open a PR.
          </p>
        </div>
      </div>

      <section className="panel">
        <h2>Create task</h2>
        <form className="form-stack" onSubmit={(e) => void createTask(e)}>
          <div className="field">
            <label htmlFor="task-req">Request</label>
            <textarea
              id="task-req"
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              placeholder="Add a /health endpoint that returns ok…"
              required
              minLength={8}
              disabled={creating}
            />
          </div>
          <div>
            <button className="btn btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create task"}
            </button>
          </div>
        </form>
      </section>

      {error ? <p className="error-text">{error}</p> : null}

      <section className="panel">
        <h2>Tasks</h2>
        {loading ? (
          <p className="loading-line">Loading tasks…</p>
        ) : tasks.length === 0 ? (
          <EmptyState title="No code tasks" detail="Create a task to propose a change." />
        ) : (
          tasks.map((task) => {
            const busy = busyId === task.id;
            return (
              <article className="task-card" key={task.id}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap" }}>
                  <strong style={{ maxWidth: "42rem" }}>{task.request}</strong>
                  <StatusBadge status={task.status} />
                </div>
                <p className="muted" style={{ margin: "0.55rem 0 0", whiteSpace: "pre-wrap" }}>{task.proposed_summary}</p>
                {task.changed_files?.length ? (
                  <div className="chip-list" style={{ marginTop: "0.65rem" }}>
                    {task.changed_files.map((f) => (
                      <span className="chip" key={f}>{f}</span>
                    ))}
                  </div>
                ) : null}

                <div className="task-actions">
                  {task.status === "ready_for_approval" ? (
                    <>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void runAction(task.id, () => api.generateCodeTask(repositoryId, task.id))}
                      >
                        {busy ? "Working…" : "Generate patch"}
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void runAction(task.id, () => api.rejectCodeTask(repositoryId, task.id))}
                      >
                        Reject
                      </button>
                    </>
                  ) : null}

                  {task.status === "patch_ready" ? (
                    <>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void runAction(task.id, () => api.approveCodeTask(repositoryId, task.id, "Approved in Otter"))}
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void runAction(task.id, () => api.rejectCodeTask(repositoryId, task.id))}
                      >
                        Reject
                      </button>
                    </>
                  ) : null}

                  {task.status === "approved" ? (
                    <button
                      className="btn btn-primary btn-sm"
                      type="button"
                      disabled={busy}
                      onClick={() => void runAction(task.id, () => api.applyCodeTask(repositoryId, task.id))}
                    >
                      Apply patch
                    </button>
                  ) : null}

                  {task.status === "applied" ? (
                    <>
                      <button
                        className="btn btn-secondary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => void handleTest(task.id)}
                      >
                        Run tests
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setPrTaskId(task.id);
                          setPrTitle(task.request.slice(0, 72));
                          setPrBody(task.proposed_summary || task.request);
                        }}
                      >
                        Open PR form
                      </button>
                    </>
                  ) : null}
                </div>

                {testResult?.taskId === task.id ? (
                  <div className="answer-block">
                    <strong>{testResult.result.passed ? "Tests passed" : "Tests failed"}</strong>
                    <pre style={{ margin: "0.5rem 0 0", whiteSpace: "pre-wrap", fontSize: "0.78rem" }}>{testResult.result.output}</pre>
                  </div>
                ) : null}

                {prResult?.taskId === task.id ? (
                  <p style={{ marginTop: "0.75rem" }}>
                    PR #{prResult.result.number}:{" "}
                    <a href={prResult.result.url} target="_blank" rel="noreferrer" style={{ color: "var(--teal-bright)" }}>
                      {prResult.result.url}
                    </a>
                  </p>
                ) : null}
              </article>
            );
          })
        )}
      </section>

      {prTaskId ? (
        <section className="panel">
          <h2>Create pull request</h2>
          <form className="form-stack" onSubmit={(e) => void handlePr(e)}>
            <div className="field">
              <label htmlFor="pr-title">Title</label>
              <input id="pr-title" value={prTitle} onChange={(e) => setPrTitle(e.target.value)} required minLength={5} />
            </div>
            <div className="field">
              <label htmlFor="pr-body">Body</label>
              <textarea id="pr-body" value={prBody} onChange={(e) => setPrBody(e.target.value)} required minLength={1} />
            </div>
            <div className="task-actions">
              <button className="btn btn-primary" type="submit" disabled={busyId === prTaskId}>
                {busyId === prTaskId ? "Opening…" : "Create pull request"}
              </button>
              <button className="btn btn-ghost" type="button" onClick={() => setPrTaskId(null)}>
                Cancel
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </div>
  );
}
