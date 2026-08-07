"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Brand } from "./Brand";
import { GitHubStatus } from "./GitHubStatus";
import { SITE_DOCS_URL } from "../lib/api";

const STORAGE_KEY = "otter.rail.collapsed";

type AppSidebarProps = {
  below?: ReactNode;
  repoLabel?: string;
};

function IconHome() {
  return (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M2.5 6.5 8 2l5.5 4.5V14a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V6.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconModels() {
  return (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M3 4.5h10M3 8h10M3 11.5h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="12.5" cy="11.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function IconDocs() {
  return (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M4 2.5h5.5L12 5v8.5H4V2.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M9.5 2.5V5H12" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

export function AppSidebar({ below, repoLabel }: AppSidebarProps) {
  const pathname = usePathname();
  const onModels = pathname.startsWith("/app/models");
  const onWorkspace = pathname === "/app" || pathname.startsWith("/app/repositories");
  const [collapsed, setCollapsed] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "1") setCollapsed(true);
      else if (stored === "0") setCollapsed(false);
      else if (window.matchMedia("(max-width: 900px)").matches) setCollapsed(true);
    } catch {
      /* ignore */
    }
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  const expanded = !collapsed || hovered;
  const railClass = [
    "studio-rail",
    collapsed ? "is-collapsed" : "is-pinned",
    hovered && collapsed ? "is-hover-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <aside
      className={railClass}
      aria-label="App navigation"
      data-expanded={expanded ? "true" : "false"}
      onMouseEnter={() => collapsed && setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="studio-rail-top">
        <div className="studio-rail-brand">
          <Brand href="/app" size="sm" />
        </div>
        <button
          type="button"
          className="studio-rail-pin"
          onClick={toggleCollapsed}
          aria-pressed={!collapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>

      <nav className="studio-rail-nav" aria-label="Primary">
        <Link
          href="/app"
          className={onWorkspace && !onModels ? "studio-rail-link active" : "studio-rail-link"}
          title="Workspace"
        >
          <span className="studio-rail-ico">
            <IconHome />
          </span>
          <span className="studio-rail-text">Workspace</span>
        </Link>
        <Link
          href="/app/models"
          className={onModels ? "studio-rail-link active" : "studio-rail-link"}
          title="Models"
        >
          <span className="studio-rail-ico">
            <IconModels />
          </span>
          <span className="studio-rail-text">Models</span>
        </Link>
      </nav>

      {below ? (
        <div className="studio-rail-repo">
          <p className="studio-rail-label">{repoLabel || "Repository"}</p>
          {below}
        </div>
      ) : null}

      <div className="studio-rail-foot">
        <a className="studio-rail-link" href={SITE_DOCS_URL} target="_blank" rel="noreferrer" title="Docs">
          <span className="studio-rail-ico">
            <IconDocs />
          </span>
          <span className="studio-rail-text">Docs</span>
        </a>
        <div className="studio-rail-profile">
          <GitHubStatus variant="rail" />
        </div>
      </div>
    </aside>
  );
}
