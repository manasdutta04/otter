import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "./Brand";

type AppShellProps = {
  children: ReactNode;
  /** Extra content on the left of the topbar (after brand). */
  left?: ReactNode;
  /** Right-side actions. */
  right?: ReactNode;
  /** Optional secondary nav row (e.g. repo tabs). */
  nav?: ReactNode;
  /** Constrain main content width. Default true. */
  narrow?: boolean;
  footer?: boolean;
};

export function AppShell({ children, left, right, nav, narrow = true, footer = true }: AppShellProps) {
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
