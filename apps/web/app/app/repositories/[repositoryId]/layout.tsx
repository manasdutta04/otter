"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";
import { AppNav } from "../../../../components/AppNav";
import { AppShell } from "../../../../components/AppShell";
import { AppSidebar } from "../../../../components/AppSidebar";
import { EmptyState } from "../../../../components/EmptyState";
import { ModelStatusChip } from "../../../../components/ModelStatusChip";
import { RepositoryProvider, useRepository } from "../../../../components/RepositoryProvider";
import { StatusBadge } from "../../../../components/StatusBadge";
import { GITHUB_LOGIN_URL } from "../../../../lib/api";

function RepoChrome({ children }: { children: ReactNode }) {
  const { repositoryId, repository, authenticated, loading, error } = useRepository();

  if (authenticated === false) {
    return (
      <AppShell
        sidebar={<AppSidebar />}
        title={<h1 className="product-page-title">Connect GitHub</h1>}
        right={<ModelStatusChip />}
      >
        <div className="auth-gate">
          <div className="connect-panel">
            <h1>Sign in to continue</h1>
            <p className="muted">Connect GitHub from the sidebar to open this repository.</p>
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
      sidebar={
        <AppSidebar
          repoLabel={repository?.name || "Repository"}
          below={<AppNav repositoryId={repositoryId} variant="rail" />}
        />
      }
      title={
        <div className="product-context">
          <div className="product-context-row">
            <h1 className="product-page-title">
              {loading && !repository ? "Loading…" : repository?.name ?? "Repository"}
            </h1>
            {repository ? <StatusBadge status={repository.status} /> : null}
          </div>
        </div>
      }
      right={
        <>
          <ModelStatusChip />
          <Link className="btn btn-ghost btn-sm" href="/app">
            All repos
          </Link>
        </>
      }
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
      <AppShell sidebar={<AppSidebar />}>
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
