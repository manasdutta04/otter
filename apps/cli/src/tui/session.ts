import readline from "node:readline";
import chalk from "chalk";
import { c } from "./theme.js";
import { renderBanner } from "./banner.js";
import { startWork } from "./work.js";
import { loadConfig, clearAuth, saveConfig } from "../config.js";
import { resolveWorkRoot, ensureProjectRepo, importRepository } from "../git/repos.js";
import { scanRepository } from "../scan/analyze.js";
import { getHealth, getIntelligence, addMemory, listMemory } from "../db/repos.js";
import { runAgent } from "../agent/loop.js";
import { loginWithBrowser } from "../auth/login.js";
import { listRemoteModels, testLlmConnection } from "../llm/client.js";
import {
  chatAboutRepo,
  generateDocs,
  latestDoc,
  latestPlan,
  planChange,
  reviewRepo,
} from "../features/workspace.js";
import { createAndMaybePr, openPrForRepo } from "../features/create.js";
import {
  CLI_PACKAGE,
  currentCliVersion,
  fetchLatestCliVersion,
  installLatestCli,
} from "../features/update.js";
import { confirmYn } from "./prompt.js";

function parseFlags(arg: string): { text: string; pr: boolean; yes: boolean } {
  const parts = arg.split(/\s+/).filter(Boolean);
  const pr = parts.includes("--pr");
  const yes = parts.includes("--yes") || parts.includes("-y");
  const text = parts.filter((p) => p !== "--pr" && p !== "--yes" && p !== "-y").join(" ");
  return { text, pr, yes };
}

/** Strip accidental prompt echoes / double prompts from pasted or glitchy input. */
function normalizeInput(raw: string): string {
  let s = raw.replace(/\r/g, "").trim();
  // "otter › otter › /create ..." → "/create ..."
  s = s.replace(/^(?:otter\s*[›>]\s*)+/gi, "").trim();
  return s;
}

async function handleSlash(
  input: string,
  ctx: { root: string; setRoot: (r: string) => void },
): Promise<"exit" | "ok"> {
  const [cmd, ...rest] = input.slice(1).trim().split(/\s+/);
  const arg = rest.join(" ").trim();
  let root = ctx.root;

  switch (cmd) {
    case "exit":
    case "quit":
    case "q":
      return "exit";
    case "help":
    case "h":
      console.log(`
  ${c.text("Understand")}
  ${c.brand("/scan")}      Scan workspace
  ${c.brand("/intel")}     Intelligence report
  ${c.brand("/health")}    Health report
  ${c.brand("/review")}    Code review
  ${c.brand("/docs")}      Generate overview docs

  ${c.text("Ask & plan")}
  ${c.brand("/chat")}      ${c.dim("<question>")} Chat about the repo
  ${c.brand("/plan")}      ${c.dim("<request>")} Implementation plan
  ${c.brand("/memory")}    ${c.dim("[add <note>]")} Project memory

  ${c.text("Build")}
  ${c.brand("/create")}    ${c.dim("<request> [--pr] [--yes]")} Code + optional PR
  ${c.brand("/pr")}        Open PR for current local changes

  ${c.text("Repos & session")}
  ${c.brand("/import")}    ${c.dim("<owner/repo>")} Clone from GitHub
  ${c.brand("/model")}     ${c.dim("[name]")} Show or set model
  ${c.brand("/login")}     GitHub login
  ${c.brand("/logout")}    Clear session
  ${c.brand("/update")}    Update CLI from npm
  ${c.brand("/clear")}     Redraw banner
  ${c.brand("/exit")}      Quit

  ${c.dim("Or type a freeform task (agent mode).")}
`);
      return "ok";
    case "update": {
      const current = currentCliVersion();
      const checkOnly = arg === "--check" || arg === "-c";
      const spin = startWork("update", "checking npm…");
      try {
        const latest = await fetchLatestCliVersion();
        if (latest === current) {
          spin.succeed(c.ok(`Already on latest (${current})`));
          return "ok";
        }
        spin.stop();
        console.log(c.muted(`  Current ${current} → latest ${latest}`));
        if (checkOnly) {
          console.log(c.dim(`  Run /update to install ${CLI_PACKAGE}@${latest}`));
          return "ok";
        }
        const ok = await confirmYn(`Install ${CLI_PACKAGE}@${latest} globally?`, true);
        if (!ok) {
          console.log(c.dim("Cancelled."));
          return "ok";
        }
        console.log(c.muted(`  Running: npm i -g ${CLI_PACKAGE}@latest`));
        await installLatestCli();
        console.log(c.ok(`✔ Updated to ${latest}. Restart otter to use the new version.`));
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
        console.log(
          c.dim(
            `  Manual: npm i -g ${CLI_PACKAGE}@latest   (or pnpm/yarn/bun global add)`,
          ),
        );
      }
      return "ok";
    }
    case "clear":
      console.clear();
      await renderBanner(root);
      return "ok";
    case "login": {
      try {
        const auth = await loginWithBrowser();
        console.log(c.ok(`✔ Logged in as ${auth.login}`));
      } catch (err) {
        console.log(c.bad(`✖ ${err instanceof Error ? err.message : String(err)}`));
      }
      return "ok";
    }
    case "logout":
      clearAuth();
      console.log(c.muted("Logged out."));
      return "ok";
    case "model": {
      const cfg = loadConfig();
      if (arg) {
        cfg.llm.model = arg;
        saveConfig(cfg);
        console.log(c.ok(`✔ Active model: ${arg}`));
        return "ok";
      }
      const spin = startWork("model");
      const models = await listRemoteModels();
      const t = await testLlmConnection();
      spin.stop();
      console.log(`  ${cfg.llm.model} @ ${cfg.llm.baseUrl}`);
      for (const m of models.slice(0, 24)) {
        console.log(m === cfg.llm.model ? c.brand(`  ● ${m}`) : c.dim(`    ${m}`));
      }
      console.log(t.ok ? c.ok("  ✔ connection ok") : c.bad(`  ✖ ${t.detail}`));
      return "ok";
    }
    case "scan": {
      const repo = ensureProjectRepo(root);
      const spin = startWork("scan", root);
      try {
        const result = await scanRepository(repo.id, root);
        spin.succeed(c.ok("Scan complete"));
        console.log(result.summary);
        console.log(c.accent(result.health.summary));
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "import": {
      if (!arg) {
        console.log(c.bad("Usage: /import owner/repo"));
        return "ok";
      }
      const spin = startWork("import", arg);
      try {
        const row = await importRepository(arg, root);
        spin.text = c.muted("Scanning import…");
        const result = await scanRepository(row.id, row.local_path);
        spin.succeed(c.ok(`Imported ${row.full_name || row.url}`));
        console.log(c.dim(row.local_path));
        console.log(result.summary);
        ctx.setRoot(row.local_path);
        console.log(c.brand(`Workspace → ${row.local_path}`));
        console.log(c.dim(`GitHub → ${row.full_name}`));
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "intel":
    case "intelligence": {
      const repo = ensureProjectRepo(root);
      let intel = getIntelligence(repo.id);
      if (!intel) {
        const spin = startWork("scan");
        await scanRepository(repo.id, root);
        spin.succeed(c.ok("Ready"));
        intel = getIntelligence(repo.id);
      }
      if (!intel) {
        console.log(c.bad("No intelligence yet."));
        return "ok";
      }
      console.log(intel.summary);
      console.log(c.dim("\nLanguages:"), intel.languages);
      return "ok";
    }
    case "health": {
      const repo = ensureProjectRepo(root);
      let health = getHealth(repo.id);
      if (!health) {
        const spin = startWork("scan");
        await scanRepository(repo.id, root);
        spin.succeed(c.ok("Ready"));
        health = getHealth(repo.id);
      }
      if (!health) {
        console.log(c.bad("No health report yet."));
        return "ok";
      }
      console.log(c.accent(health.summary));
      for (const f of health.findings.slice(0, 15)) {
        const item = f as { severity?: string; message?: string };
        console.log(`  ${c.dim(`[${item.severity}]`)} ${item.message}`);
      }
      return "ok";
    }
    case "memory": {
      const repo = ensureProjectRepo(root);
      if (arg.startsWith("add ")) {
        const id = addMemory(repo.id, arg.slice(4).trim());
        console.log(c.ok(`✔ Saved ${id}`));
        return "ok";
      }
      const rows = listMemory(repo.id);
      if (!rows.length) {
        console.log(c.dim("No memory yet. /memory add <note>"));
        return "ok";
      }
      for (const r of rows.slice(0, 20)) {
        console.log(`  ${c.dim(r.id)}  ${r.content}`);
      }
      return "ok";
    }
    case "chat": {
      if (!arg) {
        console.log(c.bad("Usage: /chat <question>"));
        return "ok";
      }
      const repo = ensureProjectRepo(root);
      const spin = startWork("agent", "chat");
      try {
        const answer = await chatAboutRepo(repo, root, arg);
        spin.succeed(c.ok("Answer"));
        console.log(answer);
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "plan": {
      if (!arg) {
        const repo = ensureProjectRepo(root);
        const last = latestPlan(repo.id);
        if (!last) {
          console.log(c.bad("Usage: /plan <request>"));
          return "ok";
        }
        console.log(c.dim(`Latest plan ${last.id} — ${last.request}`));
        console.log(last.content);
        return "ok";
      }
      const repo = ensureProjectRepo(root);
      const spin = startWork("agent", "planning");
      try {
        const plan = await planChange(repo, root, arg);
        spin.succeed(c.ok(`Plan ${plan.id}`));
        console.log(plan.content);
        console.log(c.dim("\nNext: /create <same request>  or type the task freeform"));
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "docs": {
      const repo = ensureProjectRepo(root);
      if (arg === "show") {
        const doc = latestDoc(repo.id);
        if (!doc) {
          console.log(c.dim("No docs yet. Run /docs"));
          return "ok";
        }
        console.log(c.brand(doc.title));
        console.log(doc.content);
        return "ok";
      }
      const spin = startWork("agent", "docs");
      try {
        const doc = await generateDocs(repo, root);
        spin.succeed(c.ok(doc.title));
        console.log(doc.content);
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "review": {
      const repo = ensureProjectRepo(root);
      const spin = startWork("agent", "review");
      try {
        const review = await reviewRepo(repo, root);
        spin.succeed(c.ok("Review ready"));
        console.log(review.summary);
        for (const f of review.findings) {
          console.log(`  ${c.dim(`[${f.severity}]`)} ${f.message}`);
        }
      } catch (err) {
        spin.fail(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "create": {
      const { text, pr, yes } = parseFlags(arg);
      if (!text) {
        console.log(c.bad("Usage: /create <request> [--pr] [--yes]"));
        return "ok";
      }
      const repo = ensureProjectRepo(root);
      try {
        const result = await createAndMaybePr({
          root,
          repo,
          request: text,
          openPr: pr,
          autoApprove: yes,
        });
        console.log(c.dim(`Task ${result.taskId}`));
        if (result.prUrl) console.log(c.brand(result.prUrl));
      } catch (err) {
        console.log(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    case "pr": {
      const repo = ensureProjectRepo(root);
      const title = arg || latestPlan(repo.id)?.request || "Otter changes";
      const body = latestPlan(repo.id)?.content || arg || "Changes from Otter CLI";
      try {
        await openPrForRepo(repo, root, title, body);
      } catch (err) {
        console.log(c.bad(err instanceof Error ? err.message : String(err)));
      }
      return "ok";
    }
    default:
      console.log(c.bad(`Unknown /${cmd}. Try /help`));
      return "ok";
  }
}

export async function startSession(explicitPath?: string): Promise<void> {
  let root = resolveWorkRoot(explicitPath).root;
  await renderBanner(root);

  const promptText = chalk.hex("#5EEAD4").bold("otter › ");

  const makeRl = () =>
    readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
      prompt: promptText,
    });

  let rl = makeRl();
  let busy = false;
  const queue: string[] = [];
  let closed = false;

  const attach = (interface_: readline.Interface) => {
    interface_.on("line", (line) => {
      if (busy) {
        const n = normalizeInput(line);
        if (n) queue.push(n);
        return;
      }

      void (async () => {
        busy = true;
        // Fully detach session prompt so confirms don't double-read stdin.
        interface_.close();
        try {
          let next: string | undefined = line;
          while (next !== undefined) {
            const status = await runOne(next);
            if (status === "exit") {
              console.log(c.dim("\n  🦦  Bye.\n"));
              closed = true;
              return;
            }
            next = queue.shift();
          }
        } catch (err) {
          console.error(c.bad(err instanceof Error ? err.message : String(err)));
        } finally {
          busy = false;
          if (!closed) {
            rl = makeRl();
            attach(rl);
            rl.prompt();
          }
        }
      })();
    });
  };

  const runOne = async (raw: string): Promise<"exit" | "ok"> => {
    const input = normalizeInput(raw);
    if (!input) return "ok";

    if (input.startsWith("/")) {
      return handleSlash(input, {
        root,
        setRoot: (r) => {
          root = r;
        },
      });
    }

    const allow = await confirmYn("Allow file writes & shell for this task?", true);
    console.log(c.muted(allow ? "Cooking…" : "Cooking (read-only)…"));
    try {
      await runAgent(input, {
        root,
        autoApprove: allow,
        onEvent: (msg) => console.log(msg),
      });
      console.log(c.ok("✔ Done"));
    } catch (err) {
      console.log(c.bad(`✖ ${err instanceof Error ? err.message : String(err)}`));
    }
    console.log();
    return "ok";
  };

  attach(rl);
  rl.prompt();

  await new Promise<void>((resolve) => {
    const check = setInterval(() => {
      if (closed) {
        clearInterval(check);
        resolve();
      }
    }, 200);
  });
}
