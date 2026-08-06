import { Brand } from "../components/Brand";
import { GITHUB_LOGIN_URL } from "../lib/api";

const USPS = [
  {
    title: "Repository intelligence",
    body: "Import a GitHub repo and get architecture signals, entry points, stack detection, and a grounded map of how the system fits together.",
  },
  {
    title: "Plan before code",
    body: "Ask for a change and Otter returns affected files, risks, dependencies, and verification steps you can approve before anything is written.",
  },
  {
    title: "Engineering memory",
    body: "Capture decisions and conventions once. Otter reuses them across chat, plans, and reviews so your team stops repeating the same explanations.",
  },
  {
    title: "Approval-gated coding",
    body: "Propose patches, review diffs, approve or reject, then apply and open a PR. No silent overwrites.",
  },
  {
    title: "Health and review",
    body: "Explainable scores and file-linked findings for security, maintainability, debt, and complexity — actionable, not generic LGTM.",
  },
  {
    title: "One brain, many surfaces",
    body: "The same intelligence through the web, CLI (`npx otter`), MCP, VS Code, and GitHub App.",
  },
];

export default function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Brand size="md" href="/" />
        <div className="landing-nav-actions">
          <a className="btn btn-ghost" href="/app">
            Workspace
          </a>
          <a className="btn btn-ghost" href={GITHUB_LOGIN_URL}>
            Connect GitHub
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <Brand size="hero" href={null} />
        <h1 className="landing-headline">Understand the codebase before you change it.</h1>
        <p className="landing-support">
          Otter turns repositories into engineering memory — explain architecture, plan safely, review quality, and change code only with your approval.
        </p>
        <div className="landing-ctas">
          <a className="btn btn-primary" href="/app">
            Open workspace
          </a>
          <a className="btn btn-secondary" href={GITHUB_LOGIN_URL}>
            Connect GitHub
          </a>
        </div>
      </section>

      <section className="landing-usps" id="product">
        <p className="section-kicker">Why Otter</p>
        <h2 className="section-title">Built for senior-engineer workflows</h2>
        <p className="section-lead">
          Not another chatbot. Otter focuses on understanding, planning, and quality — with coding as a controlled step.
        </p>
        <div className="usp-grid">
          {USPS.map((usp) => (
            <article key={usp.title} className="usp-block">
              <h3>{usp.title}</h3>
              <p>{usp.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-cta-band">
        <h2>Start with a repository you already care about.</h2>
        <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
          Connect GitHub ↗
        </a>
      </section>

      <footer className="landing-footer">
        <Brand size="sm" href="/" />
        <span>Otter · engineering intelligence</span>
      </footer>
    </main>
  );
}
