"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { EmptyState } from "../../../../../components/EmptyState";
import { useRepository } from "../../../../../components/RepositoryProvider";
import { api, type Memory, type MemoryKind } from "../../../../../lib/api";

export default function MemoryPage() {
  const { repositoryId, isReady, getTabCache, setTabCache } = useRepository();
  const cached = getTabCache<Memory[]>("memory");
  const [items, setItems] = useState<Memory[]>(cached ?? []);
  const [loading, setLoading] = useState(!cached);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [kind, setKind] = useState<MemoryKind>("note");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const loadMemory = useCallback(async (opts?: { force?: boolean }) => {
    if (!isReady) {
      setLoading(false);
      return;
    }
    if (!opts?.force) {
      const existing = getTabCache<Memory[]>("memory");
      if (existing) {
        setItems(existing);
        setLoading(false);
        return;
      }
    }
    setLoading(true);
    try {
      const data = await api.listMemory(repositoryId);
      setTabCache("memory", data);
      setItems(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memory");
    } finally {
      setLoading(false);
    }
  }, [isReady, repositoryId, getTabCache, setTabCache]);

  useEffect(() => {
    void loadMemory();
  }, [loadMemory]);

  async function createMemory(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createMemory(repositoryId, { kind, title: title.trim(), content: content.trim() });
      setTitle("");
      setContent("");
      setKind("note");
      await loadMemory({ force: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save memory");
    } finally {
      setSaving(false);
    }
  }

  if (!isReady) {
    return (
      <EmptyState
        title="Memory needs a ready repo"
        detail="Capture decisions and conventions after the repository import completes."
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Memory</p>
          <h1>Engineering memory</h1>
        </div>
      </div>

      <section className="panel">
        <h2>Add memory</h2>
        <form className="form-stack" onSubmit={(e) => void createMemory(e)}>
          <div className="field">
            <label htmlFor="mem-kind">Kind</label>
            <select id="mem-kind" value={kind} onChange={(e) => setKind(e.target.value as MemoryKind)} disabled={saving}>
              <option value="note">Note</option>
              <option value="decision">Decision</option>
              <option value="convention">Convention</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="mem-title">Title</label>
            <input id="mem-title" value={title} onChange={(e) => setTitle(e.target.value)} required minLength={2} disabled={saving} />
          </div>
          <div className="field">
            <label htmlFor="mem-content">Content</label>
            <textarea id="mem-content" value={content} onChange={(e) => setContent(e.target.value)} required minLength={2} disabled={saving} />
          </div>
          <div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save memory"}
            </button>
          </div>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel">
        <h2>Saved entries</h2>
        {loading ? (
          <p className="loading-line">Loading memory…</p>
        ) : items.length === 0 ? (
          <EmptyState title="No memory yet" detail="Add decisions, conventions, or notes above." />
        ) : (
          items.map((item) => (
            <article className="history-item" key={item.id}>
              <div className="chip-list" style={{ marginBottom: "0.45rem" }}>
                <span className="chip">{item.kind}</span>
              </div>
              <strong>{item.title}</strong>
              <p className="muted" style={{ whiteSpace: "pre-wrap", marginBottom: "0.35rem" }}>{item.content}</p>
              <div className="muted" style={{ fontSize: "0.75rem" }}>{new Date(item.created_at).toLocaleString()}</div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
