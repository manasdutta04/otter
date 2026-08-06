import { Brand } from "../components/Brand";
import { GITHUB_LOGIN_URL } from "../lib/api";

const FEATURE_CARDS = [
  { icon: "🗺️", title: "Repository intelligence", caption: "Map any GitHub codebase" },
  { icon: "🧭", title: "Plan before code", caption: "Risks, files, verification" },
  { icon: "✅", title: "Approval-gated patches", caption: "Approve before apply" },
  { icon: "🧠", title: "Engineering memory", caption: "Decisions that stick" },
];

const FEATURE_ROWS = [
  {
    id: "understand",
    title: "Understand repositories locally",
    body: "Import a GitHub repo and get architecture signals, entry points, stack detection, and a grounded map of how the system fits together — before anyone writes a line of code.",
    placeholder: "Architecture map preview",
    cta: { label: "Open workspace", href: "/app" },
  },
  {
    id: "plan",
    title: "No-guesswork planning",
    body: "Ask for a change and Otter returns affected files, risks, dependencies, and verification steps. Approve the plan before any patch is proposed.",
    placeholder: "Planner + affected files",
    cta: { label: "Start for free", href: GITHUB_LOGIN_URL },
    reverse: true,
  },
  {
    id: "coding",
    title: "Approval-gated coding",
    body: "Propose patches, review diffs, approve or reject, then apply and open a PR. Otter never silently overwrites your source tree.",
    placeholder: "Diff review + PR flow",
    cta: { label: "Connect GitHub", href: GITHUB_LOGIN_URL },
  },
  {
    id: "memory",
    title: "Engineering memory that compounds",
    body: "Capture decisions and conventions once. Otter reuses them across chat, plans, and reviews so your team stops repeating the same explanations.",
    placeholder: "Memory timeline",
    cta: { label: "Open workspace", href: "/app" },
    reverse: true,
  },
];

const STATS = [
  { icon: "⚡", title: "Understand first", body: "Architecture before patches" },
  { icon: "🛡", title: "Human approval", body: "Nothing lands without a yes" },
  { icon: "🔗", title: "Web · CLI · MCP", body: "One brain across surfaces" },
];

const FOOTER = {
  product: [
    { label: "Workspace", href: "/app" },
    { label: "Connect GitHub", href: GITHUB_LOGIN_URL },
    { label: "Why Otter", href: "#why" },
  ],
  company: [
    { label: "Product", href: "#product" },
    { label: "GitHub", href: "https://github.com/manasdutta04/veridexs" },
  ],
  community: [
    { label: "GitHub", href: "https://github.com/manasdutta04/veridexs" },
    { label: "Start for free", href: GITHUB_LOGIN_URL },
  ],
};

export default function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Brand size="md" href="/" />
        <nav className="landing-nav-links" aria-label="Product">
          <a href="#product">Product</a>
          <a href="/app">Workspace</a>
          <a href="#why">Why Otter ✨</a>
          <a href="https://github.com/manasdutta04/veridexs" target="_blank" rel="noreferrer">
            Docs
          </a>
        </nav>
        <div className="landing-nav-actions">
          <a
            className="btn btn-outline btn-sm"
            href="https://github.com/manasdutta04/veridexs"
            target="_blank"
            rel="noreferrer"
          >
            ★ Star
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <a className="landing-badge" href="/app">
          New ✨ Introducing Otter workspace
        </a>
        <h1 className="landing-headline">
          <span className="script">Easily</span> understand &amp; change codebases.
        </h1>
        <div className="landing-ctas">
          <a className="btn btn-secondary" href={GITHUB_LOGIN_URL}>
            Connect GitHub
          </a>
          <a className="btn btn-primary" href="/app">
            Start for free
          </a>
        </div>
      </section>

      <div className="landing-cards" aria-label="Highlights">
        {FEATURE_CARDS.map((card) => (
          <a className="landing-card" href="/app" key={card.title}>
            <div className="landing-card-media" aria-hidden="true">
              <span className="landing-card-emoji">{card.icon}</span>
              <span className="landing-card-fakeui">
                <span />
                <span />
                <span />
              </span>
            </div>
            <strong>{card.caption}</strong>
          </a>
        ))}
      </div>

      <div className="landing-sections" id="product">
        {FEATURE_ROWS.map((row) => (
          <section
            key={row.id}
            className={row.reverse ? "feature-row feature-row-reverse" : "feature-row"}
            id={row.id}
          >
            <div className="feature-copy">
              <h2>{row.title}</h2>
              <p>{row.body}</p>
              <a className="btn btn-primary" href={row.cta.href}>
                {row.cta.label}
              </a>
            </div>
            <div className="feature-media" aria-hidden="true">
              <div className="media-placeholder">
                <div className="media-placeholder-chrome">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="media-placeholder-body">
                  <div className="media-placeholder-sidebar" />
                  <div className="media-placeholder-main">
                    <div className="media-placeholder-line long" />
                    <div className="media-placeholder-line mid" />
                    <div className="media-placeholder-line short" />
                    <div className="media-placeholder-card" />
                  </div>
                </div>
                <p className="media-placeholder-label">{row.placeholder}</p>
              </div>
            </div>
          </section>
        ))}
      </div>

      <section className="landing-band" id="why">
        <h2 className="section-title">
          Ship with Otter in <span className="accent">hours</span>, not weeks.
        </h2>
        <div className="landing-stats">
          {STATS.map((stat) => (
            <div className="stat-cell" key={stat.title}>
              <span className="usp-icon" aria-hidden="true">
                {stat.icon}
              </span>
              <div>
                <strong>{stat.title}</strong>
                <span>{stat.body}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-band landing-believe">
        <h2 className="section-title">Don&apos;t believe us?</h2>
        <p className="section-lead">
          Try the fully free open-source path. Import a repo you already care about and see grounded intelligence in minutes.
        </p>
        <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
          Get access now
        </a>
      </section>

      <section className="landing-newsletter">
        <div className="newsletter-card">
          <h2>Don&apos;t forget to follow along</h2>
          <p className="muted">Product updates as Otter ships CLI, MCP, and deeper review tooling.</p>
          <form className="newsletter-form" action="/app" method="get">
            <input type="email" name="email" placeholder="you@company.com" aria-label="Email" required />
            <button className="btn btn-primary" type="submit">
              Notify me
            </button>
          </form>
        </div>
      </section>

      <section className="landing-cta-band">
        <h2>Ready to use otter?</h2>
        <a className="btn btn-primary" href={GITHUB_LOGIN_URL}>
          Get started for free
        </a>
      </section>

      <footer className="site-footer">
        <div className="site-footer-top">
          <div className="site-footer-brand">
            <Brand size="md" href="/" />
            <p className="muted">Engineering intelligence for modern teams.</p>
          </div>
          <div className="site-footer-cols">
            <div>
              <h3>Product</h3>
              <ul>
                {FOOTER.product.map((item) => (
                  <li key={item.label}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Company</h3>
              <ul>
                {FOOTER.company.map((item) => (
                  <li key={item.label}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Community</h3>
              <ul>
                {FOOTER.community.map((item) => (
                  <li key={item.label}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="site-footer-bottom">
          <span>© {new Date().getFullYear()} otter. All rights reserved.</span>
          <span className="muted">Understand → Explain → Plan → Review → Build</span>
        </div>
      </footer>
    </main>
  );
}
