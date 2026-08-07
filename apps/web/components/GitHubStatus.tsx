"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, GITHUB_LOGIN_URL } from "../lib/api";

type MeState = {
  authenticated: boolean;
  login: string | null;
  avatar_url: string | null;
};

type GitHubStatusProps = {
  /** `rail` = Studio sidebar profile control; `bar` = compact topbar (legacy). */
  variant?: "rail" | "bar";
};

export function GitHubStatus({ variant = "bar" }: GitHubStatusProps) {
  const [me, setMe] = useState<MeState | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.getMe();
      setMe({
        authenticated: Boolean(data.authenticated),
        login: data.login ?? null,
        avatar_url: data.avatar_url ?? null,
      });
    } catch {
      setMe({ authenticated: false, login: null, avatar_url: null });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!open) return;
    function onDoc(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function disconnect() {
    setBusy(true);
    try {
      await api.logout();
      setMe({ authenticated: false, login: null, avatar_url: null });
      setOpen(false);
      if (typeof window !== "undefined" && window.location.pathname.startsWith("/app/repositories")) {
        window.location.href = "/app";
        return;
      }
      window.location.reload();
    } catch {
      setBusy(false);
    }
  }

  const rootClass = variant === "rail" ? "gh-status gh-status-rail" : "gh-status";

  if (!me) {
    return <span className="muted gh-status-loading">…</span>;
  }

  if (!me.authenticated) {
    return (
      <a
        className={variant === "rail" ? "studio-rail-link gh-connect" : "btn btn-primary btn-sm"}
        href={GITHUB_LOGIN_URL}
        title="Connect GitHub"
      >
        {variant === "rail" ? (
          <>
            <span className="studio-rail-ico" aria-hidden>
              <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
              </svg>
            </span>
            <span className="studio-rail-text">Connect GitHub</span>
          </>
        ) : (
          "Connect GitHub"
        )}
      </a>
    );
  }

  return (
    <div className={rootClass} ref={rootRef}>
      <button
        type="button"
        className={variant === "rail" ? "gh-status-trigger rail" : "gh-status-trigger"}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        title={`GitHub · @${me.login || "connected"}`}
      >
        {me.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="gh-status-avatar" src={me.avatar_url} alt="" width={22} height={22} />
        ) : (
          <span className="gh-status-mark" aria-hidden>
            GH
          </span>
        )}
        <span className="gh-status-label studio-rail-text">@{me.login || "connected"}</span>
      </button>
      {open ? (
        <div className="gh-status-menu" role="menu">
          <p className="gh-status-menu-meta">Otter GitHub App · import &amp; PRs</p>
          <button type="button" role="menuitem" disabled={busy} onClick={() => void disconnect()}>
            {busy ? "Disconnecting…" : "Disconnect"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
