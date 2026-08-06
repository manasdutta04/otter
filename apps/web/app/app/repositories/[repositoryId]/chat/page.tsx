"use client";

import { FormEvent, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api } from "../../../../../lib/api";

export default function ChatPage() {
  const { repositoryId, isReady } = useRepository();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.chat(repositoryId, question.trim());
      setAnswer(data.answer);
      setSources(data.sources ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
      setAnswer("");
      setSources([]);
    } finally {
      setLoading(false);
    }
  }

  if (!isReady) {
    return (
      <EmptyState
        title="Chat unlocks when ready"
        detail="Grounded semantic chat needs a finished import so answers can cite real source files."
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Chat</p>
          <h1>Ask the codebase</h1>
        </div>
      </div>

      <section className="panel">
        <form className="form-stack" onSubmit={(e) => void ask(e)}>
          <div className="field">
            <label htmlFor="chat-q">Question</label>
            <textarea
              id="chat-q"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Where is authentication handled?"
              required
              disabled={loading}
              minLength={2}
            />
          </div>
          <div>
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? "Searching…" : "Ask"}
            </button>
          </div>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
        {answer ? <div className="answer-block">{answer}</div> : null}
        {sources.length > 0 ? (
          <div style={{ marginTop: "1rem" }}>
            <h3>Sources</h3>
            <div className="chip-list">
              {sources.map((s) => (
                <span className="chip" key={s}>{s}</span>
              ))}
            </div>
          </div>
        ) : null}
        {!answer && !error && !loading ? (
          <p className="muted" style={{ marginBottom: 0, marginTop: "1rem" }}>
            Answers include citations from repository files when available.
          </p>
        ) : null}
      </section>
    </div>
  );
}
