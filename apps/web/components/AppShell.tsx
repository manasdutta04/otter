import type { ReactNode } from "react";
import { Brand } from "./Brand";

type AppShellProps = {
  children: ReactNode;
  left?: ReactNode;
  right?: ReactNode;
  nav?: ReactNode;
  sidebar?: ReactNode;
  title?: ReactNode;
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
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-left">
          <Brand href="/app" size="sm" />
          {left}
        </div>
        <div className="app-topbar-meta">{right}</div>
      </header>
      {nav}
      <main className={narrow ? "app-main" : "app-main app-main-wide"}>{children}</main>
    </div>
  );
}
