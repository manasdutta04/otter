"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type ReactNode } from "react";
import { AppNav } from "../../../../components/AppNav";
import { AppShell } from "../../../../components/AppShell";
import { EmptyState } from "../../../../components/EmptyState";
import { ModelStatusChip } from "../../../../components/ModelStatusChip";
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
      <AppShell
        right={
          <a className="btn btn-primary btn-sm" href={GITHUB_LOGIN_URL}>
            Connect GitHub
          </a>
        }
      >
        <div className="auth-gate">
          <div className="connect-panel">
            <p className="eyebrow">Sign in</p>
            <h1>Connect GitHub</h1>
            <p className="muted">Sign in to open this repository workspace.</p>
            <div style={{ marginTop: "1.25rem" }}>
              <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
                Connect GitHub
              </a>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      left={
        <>
          <nav className="studio-links" aria-label="Studio">
            <Link href="/app">Workspace</Link>
            <Link href="/app/models">Models</Link>
          </nav>
          <div className="repo-chrome-title">
            <h1>{loading && !repository ? "Loading…" : repository?.name ?? "Repository"}</h1>
            {repository ? <StatusBadge status={repository.status} /> : null}
          </div>
        </>
      }
      right={
        <>
          <ModelStatusChip />
          <button className="btn btn-outline btn-sm" type="button" onClick={() => void handleLogout()} disabled={loggingOut}>
            {loggingOut ? "Logging out…" : "Log out"}
          </button>
        </>
      }
      nav={<AppNav repositoryId={repositoryId} />}
    >
      {error ? (
        <EmptyState
          title="Couldn’t load repository"
          detail={error}
          action={
            <Link className="btn btn-outline" href="/app">
              Back to workspace
            </Link>
          }
        />
      ) : (
        children
      )}
    </AppShell>
  );
}

export default function RepositoryLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ repositoryId: string | string[] }>();
  const repositoryId = Array.isArray(params.repositoryId) ? params.repositoryId[0] : params.repositoryId;

  if (!repositoryId) {
    return (
      <AppShell>
        <EmptyState title="Missing repository" detail="No repository id in the URL." />
      </AppShell>
    );
  }

  return (
    <RepositoryProvider repositoryId={repositoryId}>
      <RepoChrome>{children}</RepoChrome>
    </RepositoryProvider>
  );
}
