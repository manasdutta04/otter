import { Brand } from "../components/Brand";
import { PressSlot } from "../components/PressSlot";
import { APP_MODELS, APP_WORKSPACE, GITHUB_REPO } from "../lib/urls";

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
          <a href={APP_WORKSPACE}>Workspace</a>
          <a href={APP_MODELS}>Models</a>
        </nav>
        <div className="landing-nav-actions">
          <a className="github-star-btn" href={GITHUB_REPO} target="_blank" rel="noreferrer">
            <GitHubMark />
            <span>Star on GitHub</span>
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <a className="landing-badge" href={APP_WORKSPACE}>
          New ✨ Introducing Otter workspace
        </a>
        <h1 className="landing-headline">
          <span className="script">Easily</span> understand &amp; change codebases.
        </h1>
        <div className="landing-ctas">
          <a className="btn btn-secondary" href="/docs/self-host">
            Self-host with Docker
          </a>
          <a className="btn btn-primary" href={APP_WORKSPACE}>
            Start for free
          </a>
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
            <a className="btn btn-outline" href={APP_WORKSPACE}>
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="workspace.png" label="Workspace UI" caption="Import · repo list · status" />
          </div>
        </section>

        <section className="feature-row feature-row-reverse">
          <div className="feature-copy">
            <h2>Connect a free local model</h2>
            <p>
              Point Otter at Ollama on your machine (or any OpenAI-compatible endpoint). One Models
              page — used for chat, explain, and coding.
            </p>
            <a className="btn btn-outline" href={APP_MODELS}>
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="models.png" label="Models UI" caption="Providers · discovery · test" />
          </div>
        </section>

        <section className="feature-row">
          <div className="feature-copy">
            <h2>Ask the codebase</h2>
            <p>
              Grounded chat cites real files. Plan changes with risks and verification steps before
              any patch is proposed.
            </p>
            <a className="btn btn-outline" href={APP_WORKSPACE}>
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="chat.png" label="Chat UI" caption="Grounded answers · citations" />
          </div>
        </section>

        <section className="feature-row feature-row-reverse">
          <div className="feature-copy">
            <h2>Approval-gated coding</h2>
            <p>
              Generate patches, review diffs, approve or reject, then open a PR. Otter never silently
              overwrites your source tree.
            </p>
            <a className="btn btn-outline" href={APP_WORKSPACE}>
              Learn more
            </a>
          </div>
          <div className="feature-media">
            <PressSlot file="coding.png" label="Coding UI" caption="Diff · approve · PR" />
          </div>
        </section>
      </div>

      <section className="landing-band landing-believe">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="believe-art" src="/landing/otter-magnify.png" alt="" />
        <h2 className="section-title">Don&apos;t believe us?</h2>
        <p className="section-lead">
          Try the fully free open-source path. Import a repo you already care about and see grounded
          intelligence in minutes.
        </p>
        <a className="btn btn-primary" href={APP_WORKSPACE}>
          Get access now
        </a>
      </section>

      <section className="landing-band" id="why">
        <h2 className="section-title">
          Ship with Otter in <span className="accent">hours</span>, not weeks.
        </h2>
        <div className="landing-stats">
          <div className="stat-cell">
            <strong>Understand first</strong>
            <span>Architecture before patches</span>
          </div>
          <div className="stat-cell">
            <strong>Human approval</strong>
            <span>Nothing lands without a yes</span>
          </div>
          <div className="stat-cell">
            <strong>Web · CLI · MCP</strong>
            <span>One brain across surfaces</span>
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
            <h3>Don&apos;t forget to follow along</h3>
            <a className="btn btn-outline btn-sm" href={APP_WORKSPACE}>
              Open workspace
            </a>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/landing/otter-magnify.png" alt="" />
          </article>
        </div>
      </section>

      <section className="landing-cta-band">
        <h2>Ready to use otter?</h2>
        <a className="btn btn-primary" href={APP_WORKSPACE}>
          Get started for free
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
                <a href={APP_WORKSPACE}>Workspace</a>
              </li>
              <li>
                <a href="/docs/docker">Docker</a>
              </li>
              <li>
                <a href="/docs/self-host">Self-host</a>
              </li>
              <li>
                <a href={APP_MODELS}>Models</a>
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
                <a href={APP_WORKSPACE}>Start for free</a>
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
