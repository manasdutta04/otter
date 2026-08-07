import { Brand } from "../../components/Brand";
import { APP_WORKSPACE, GITHUB_REPO } from "../../lib/urls";
import type { ReactNode } from "react";

const DOC_LINKS = [
  { href: "/docs", label: "Overview" },
  { href: "/docs/self-host", label: "Self-host" },
  { href: "/docs/docker", label: "Docker" },
  { href: "/docs/models", label: "Models" },
  { href: "/docs/github", label: "GitHub" },
  { href: "/docs/cli", label: "CLI" },
];

export default function DocsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="docs-page">
      <header className="landing-nav">
        <Brand href="/" size="md" />
        <nav className="landing-nav-links" aria-label="Product">
          <a href="/#product">Product</a>
          <a href="/docs">Docs</a>
          <a href={APP_WORKSPACE}>Workspace</a>
          <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
        <div className="landing-nav-actions">
          <a className="btn btn-primary btn-sm" href={APP_WORKSPACE}>
            Start for free
          </a>
        </div>
      </header>
      <div className="docs-shell">
        <aside className="docs-nav" aria-label="Documentation">
          <p className="docs-nav-label">Docs</p>
          {DOC_LINKS.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </aside>
        <article className="docs-article">{children}</article>
      </div>
    </div>
  );
}
