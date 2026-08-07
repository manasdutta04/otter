"use client";

import { FormEvent, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type ChatResponse } from "../../../../../lib/api";

export default function ChatPage() {
  const { repositoryId, isReady } = useRepository();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.chat(repositoryId, question.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  if (!isReady) {
    return (
      <EmptyState
        title="Chat unlocks when ready"
        detail="Grounded chat needs a finished import so answers can cite real source files."
      />
    );
  }

  const lead = result?.answer?.split("\n\n")[0] ?? "";
  const related = result?.answer?.split("\n\n").slice(1).join(" ").trim() ?? "";

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Chat</h1>
          <p className="page-lede">Ask like a teammate. Answers cite files from this repository.</p>
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
              placeholder="Where does Solana wallet connection happen?"
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
      </section>

      {result ? (
        <section className="chat-answer">
          <p className="chat-lead">{lead.replace(/`([^`]+)`/g, "$1")}</p>

          {result.primary_file ? (
            <div className="chat-file-card">
              <div className="chat-file-meta">
                <span className="chat-file-path">{result.primary_file}</span>
                {result.primary_lines ? <span className="chat-file-lines">{result.primary_lines}</span> : null}
              </div>
              {result.excerpt ? <p className="chat-excerpt">{result.excerpt}</p> : null}
            </div>
          ) : null}

          {related ? <p className="chat-related">{related.replace(/`([^`]+)`/g, "$1")}</p> : null}

          {(result.sources ?? []).length > 0 ? (
            <div className="chat-sources">
              <span className="chat-sources-label">Sources</span>
              <ul className="plain-list">
                {result.sources.map((source) => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
