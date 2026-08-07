import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "./Brand";

type AppShellProps = {
  children: ReactNode;
  /** Extra content on the left of the topbar (after brand). Legacy; prefer sidebar. */
  left?: ReactNode;
  /** Right-side actions in the top context bar. */
  right?: ReactNode;
  /** Optional secondary nav row (legacy horizontal tabs). */
  nav?: ReactNode;
  /** Studio left rail (Archestra/Unsloth-style). */
  sidebar?: ReactNode;
  /** Title / context shown in the top bar when using sidebar layout. */
  title?: ReactNode;
  /** Constrain main content width. Default true. */
  narrow?: boolean;
  footer?: boolean;
};

export function AppShell({
  children,
  left,
  right,
  nav,
  sidebar,
  title,
  narrow = true,
  footer = true,
}: AppShellProps) {
  if (sidebar) {
    return (
      <div className="studio-shell">
        {sidebar}
        <div className="studio-stage">
          <header className="studio-topbar">
            <div className="studio-topbar-title">{title}</div>
            <div className="studio-topbar-actions">{right}</div>
          </header>
          <main className={narrow ? "studio-main" : "studio-main studio-main-wide"}>{children}</main>
          {footer ? (
            <footer className="studio-footer">
              <span className="muted">Otter Studio</span>
              <div className="app-footer-links">
                <Link href="/">Home</Link>
                <Link href="/app">Workspace</Link>
              </div>
            </footer>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-left">
          <Brand href="/" size="sm" />
          {left}
        </div>
        <div className="app-topbar-meta">{right}</div>
      </header>
      {nav}
      <main className={narrow ? "app-main" : "app-main app-main-wide"}>{children}</main>
      {footer ? (
        <footer className="app-footer">
          <Brand size="sm" href="/" />
          <div className="app-footer-links">
            <Link href="/">Home</Link>
            <Link href="/app">Workspace</Link>
            <a href="https://github.com/manasdutta04/veridexs" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </div>
          <span className="muted">© {new Date().getFullYear()} otter</span>
        </footer>
      ) : null}
    </div>
  );
}
