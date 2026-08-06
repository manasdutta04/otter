"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type ReactNode } from "react";
import { AppNav } from "../../../../components/AppNav";
import { Brand } from "../../../../components/Brand";
import { EmptyState } from "../../../../components/EmptyState";
import { RepositoryProvider, useRepository } from "../../../../components/RepositoryProvider";
import { StatusBadge } from "../../../../components/StatusBadge";
import { api, GITHUB_LOGIN_URL } from "../../../../lib/api";

function RepoChrome({ children }: { children: ReactNode }) {
  const { repositoryId, repository, authenticated, loading, error } = useRepository();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await api.logout();
    } catch {
      /* ignore */
    } finally {
      window.location.href = "/app";
    }
  }

  if (authenticated === false) {
    return (
      <div className="app-shell">
        <header className="app-topbar">
          <Brand href="/" size="md" />
        </header>
        <div className="auth-gate">
          <div className="connect-panel">
            <Brand href={null} size="lg" />
            <h1>Connect GitHub</h1>
            <p className="muted">Sign in to open this repository workspace.</p>
            <div style={{ marginTop: "1.25rem" }}>
              <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
                Connect GitHub
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <Brand href="/" size="sm" />
          <Link className="btn btn-ghost btn-sm" href="/app">
            ← Workspace
          </Link>
          <div className="repo-chrome-title">
            <h1>{loading && !repository ? "Loading…" : repository?.name ?? "Repository"}</h1>
            {repository ? <StatusBadge status={repository.status} /> : null}
          </div>
        </div>
        <div className="app-topbar-meta">
          <button className="btn btn-secondary btn-sm" type="button" onClick={() => void handleLogout()} disabled={loggingOut}>
            {loggingOut ? "Logging out…" : "Log out"}
          </button>
        </div>
      </header>

      <AppNav repositoryId={repositoryId} />

      <main className="app-main">
        {error ? (
          <EmptyState title="Couldn’t load repository" detail={error} action={<Link className="btn btn-secondary" href="/app">Back to workspace</Link>} />
        ) : (
          children
        )}
      </main>
    </div>
  );
}

export default function RepositoryLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ repositoryId: string | string[] }>();
  const repositoryId = Array.isArray(params.repositoryId) ? params.repositoryId[0] : params.repositoryId;

  if (!repositoryId) {
    return (
      <div className="app-shell">
        <main className="app-main">
          <EmptyState title="Missing repository" detail="No repository id in the URL." />
        </main>
      </div>
    );
  }

  return (
    <RepositoryProvider repositoryId={repositoryId}>
      <RepoChrome>{children}</RepoChrome>
    </RepositoryProvider>
  );
}
