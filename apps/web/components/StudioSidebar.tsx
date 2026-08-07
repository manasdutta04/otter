"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Brand } from "./Brand";

type StudioSidebarProps = {
  /** Extra block under studio links (usually repo nav). */
  below?: ReactNode;
  repoLabel?: string;
};

export function StudioSidebar({ below, repoLabel }: StudioSidebarProps) {
  const pathname = usePathname();
  const onModels = pathname.startsWith("/app/models");
  const onWorkspace = pathname === "/app" || pathname.startsWith("/app/repositories");

  return (
    <aside className="studio-rail" aria-label="Studio navigation">
      <div className="studio-rail-brand">
        <Brand href="/" size="sm" />
        <span className="studio-rail-tag">Studio</span>
      </div>

      <div className="studio-rail-section">
        <p className="studio-rail-label">Studio</p>
        <nav className="studio-rail-nav">
          <Link
            href="/app"
            className={onWorkspace && !onModels ? "studio-rail-link active" : "studio-rail-link"}
          >
            <span className="studio-rail-ico" aria-hidden>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path
                  d="M2.5 6.5 8 2l5.5 4.5V14a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V6.5Z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            Workspace
          </Link>
          <Link href="/app/models" className={onModels ? "studio-rail-link active" : "studio-rail-link"}>
            <span className="studio-rail-ico" aria-hidden>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <path
                  d="M3 4.5h10M3 8h10M3 11.5h6"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
                <circle cx="12.5" cy="11.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            </span>
            Models
          </Link>
        </nav>
      </div>

      {below ? (
        <div className="studio-rail-section studio-rail-repo">
          <p className="studio-rail-label">{repoLabel || "Repository"}</p>
          {below}
        </div>
      ) : null}

      <div className="studio-rail-foot">
        <Link href="/" className="studio-rail-foot-link">
          Marketing site
        </Link>
        <p className="muted">Understand → Explain → Plan → Build</p>
      </div>
    </aside>
  );
}
