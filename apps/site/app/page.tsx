import { Brand } from "../components/Brand";
import { CopyCommand } from "../components/CopyCommand";
import { PressSlot } from "../components/PressSlot";
import { DOCKER_HUB, GITHUB_REPO } from "../lib/urls";

function GitHubMark({ className }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

export default function LandingPage() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Brand size="md" href="/" />
        <nav className="landing-nav-links" aria-label="Product">
          <a href="#product">Product</a>
          <a href="/docs">Docs</a>
          <a href="/docs/self-host">Self-host</a>
          <a href="/docs/docker">Docker</a>
        </nav>
        <div className="landing-nav-actions">
          <a className="github-star-btn" href={GITHUB_REPO} target="_blank" rel="noreferrer">
            <GitHubMark />
            <span>Star</span>
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-copy">
          <a className="landing-badge" href="/docs/self-host">
            New ✨ Docker + Otter GitHub App
          </a>
          <h1 className="landing-headline">
            <span className="script">Easily</span> understand &amp; change code
          </h1>
          <CopyCommand className="landing-copy-pill" useComposeUrl variant="button" />
          <p className="landing-privacy-note">
            Runs on your machine. Local DB and repos stay private. Connect GitHub via the Otter app.
          </p>
          <div className="landing-ctas">
            <a className="btn btn-secondary" href="/docs/self-host">
              Setup guide
            </a>
            <a className="btn btn-outline" href={DOCKER_HUB} target="_blank" rel="noreferrer">
              Docker Hub
            </a>
          </div>
        </div>
        <div className="landing-hero-visual landing-hero-mascot">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/landing/otter-confeti.png" alt="" />
        </div>
      </section>

      <div className="landing-sections" id="product">
        <section className="feature-row">
          <div className="feature-copy">
            <h2>Understand repositories locally</h2>
            <p>
              Import a GitHub repo and get architecture signals, entry points, and stack detection —
              before anyone writes a line of code.
            </p>
            <a className="btn btn-outline" href="/docs/self-host">
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="Workspace-UI.png" label="Workspace UI" caption="Import · repo list · status" />
          </div>
        </section>

        <section className="feature-row feature-row-reverse">
          <div className="feature-copy">
            <h2>Connect a free local model</h2>
            <p>
              Point Otter at Ollama on your machine (or any OpenAI-compatible endpoint). One Models
              page — used for chat, explain, and coding.
            </p>
            <a className="btn btn-outline" href="/docs/models">
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="Models-UI.png" label="Models UI" caption="Providers · discovery · test" />
          </div>
        </section>

        <section className="feature-row">
          <div className="feature-copy">
            <h2>Ask the codebase</h2>
            <p>
              Grounded chat cites real files. Plan changes with risks and verification steps before
              any patch is proposed.
            </p>
            <a className="btn btn-outline" href="/docs">
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="Chat-UI.png" label="Chat UI" caption="Grounded answers · citations" />
          </div>
        </section>

        <section className="feature-row feature-row-reverse">
          <div className="feature-copy">
            <h2>Approval-gated coding</h2>
            <p>
              Generate patches, review diffs, approve or reject, then open a PR. Otter never silently
              overwrites your source tree.
            </p>
            <a className="btn btn-outline" href="/docs">
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="Coding-UI.png" label="Coding UI" caption="Diff · approve · PR" />
          </div>
        </section>
      </div>

      <section className="landing-band" id="why">
        <h2 className="section-title section-title-wide">
          Ship with Otter in <span className="accent">Fast</span>.
        </h2>
        <div className="landing-stats">
          <div className="stat-cell">
            <span className="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.5-3.5" />
                <path d="M8.5 11h5M11 8.5v5" />
              </svg>
            </span>
            <p className="stat-text">Understand first · architecture before patches</p>
          </div>
          <div className="stat-cell">
            <span className="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
                <path d="M9.5 12l1.8 1.8L15 10" />
              </svg>
            </span>
            <p className="stat-text">Human approval · nothing lands without a yes</p>
          </div>
          <div className="stat-cell">
            <span className="stat-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3l8 4-8 4-8-4 8-4z" />
                <path d="M4 11l8 4 8-4" />
                <path d="M4 15l8 4 8-4" />
              </svg>
            </span>
            <p className="stat-text">Web · CLI · MCP · one brain across surfaces</p>
          </div>
        </div>
      </section>

      <section className="landing-details-wrap">
        <p className="section-kicker">The details</p>
        <h2 className="section-title">We&apos;re making engineering intelligence accessible</h2>
        <div className="details-mint">
          <div>
            <p>
              As AI coding tools rush to write files first, Otter starts with understanding. Run it on
              your machine, bring your own model, and keep approval before every write.
            </p>
            <a className="btn btn-outline" href="/docs">
              Find out more
            </a>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/landing/otter-phone.png" alt="" />
        </div>
        <div className="details-mini-grid">
          <article className="details-mini mint">
            <h3>Self-host on Docker</h3>
            <a className="btn btn-outline btn-sm" href="/docs/docker">
              Docker docs
            </a>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/landing/otter-docker.png" alt="" />
          </article>
          <article className="details-mini lavender">
            <h3>Copy, run, open the app</h3>
            <a className="btn btn-outline btn-sm" href="/docs/self-host">
              Self-host guide
            </a>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/landing/otter-magnify.png" alt="" />
          </article>
        </div>
      </section>

      <section className="landing-cta-band">
        <h2>Ready to run Otter?</h2>
        <CopyCommand className="landing-copy-pill" useComposeUrl variant="button" />
        <a className="btn btn-secondary" href="/docs/self-host">
          Full setup guide
        </a>
      </section>

      <footer className="site-footer site-footer-columns">
        <div className="site-footer-grid">
          <div>
            <h3>Company</h3>
            <ul>
              <li>
                <a href="#why">About</a>
              </li>
              <li>
                <a href="#product">Product</a>
              </li>
              <li>
                <a href="/docs">Docs</a>
              </li>
            </ul>
          </div>
          <div>
            <h3>Product</h3>
            <ul>
              <li>
                <a href="/docs/self-host">Self-host</a>
              </li>
              <li>
                <a href="/docs/docker">Docker</a>
              </li>
              <li>
                <a href="/docs/models">Models</a>
              </li>
              <li>
                <a href="/docs/cli">CLI</a>
              </li>
            </ul>
          </div>
          <div>
            <h3>Community</h3>
            <ul>
              <li>
                <a href={GITHUB_REPO} target="_blank" rel="noreferrer">
                  GitHub
                </a>
              </li>
              <li>
                <a href={DOCKER_HUB} target="_blank" rel="noreferrer">
                  Docker Hub
                </a>
              </li>
            </ul>
          </div>
          <div className="site-footer-brand-col">
            <Brand size="md" href="/" />
            <p className="muted">Engineering intelligence for modern teams.</p>
            <a className="github-star-btn" href={GITHUB_REPO} target="_blank" rel="noreferrer">
              <GitHubMark />
              <span>Star on GitHub</span>
            </a>
          </div>
        </div>
        <div className="site-footer-bottom">
          <span>© {new Date().getFullYear()} otter. All rights reserved.</span>
        </div>
      </footer>
    </main>
  );
}
