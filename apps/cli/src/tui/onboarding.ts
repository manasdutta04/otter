import * as p from "@clack/prompts";
import { c } from "./theme.js";
import { loadConfig, saveConfig } from "../config.js";
import { loginWithBrowser } from "../auth/login.js";
import { listRemoteModels, testLlmConnection } from "../llm/client.js";
import { startWork } from "./work.js";

export async function runOnboarding(): Promise<void> {
  p.intro(`${c.brand("🦦 Otter")} setup`);

  const method = await p.select({
    message: "Select login method",
    options: [
      {
        value: "github",
        label: "GitHub via Otter broker",
        hint: "import repos & open PRs",
      },
      {
        value: "skip",
        label: "Continue without GitHub",
        hint: "local scan & chat only",
      },
    ],
  });

  if (p.isCancel(method)) {
    p.cancel("Setup cancelled.");
    process.exit(0);
  }

  if (method === "github") {
    p.log.step("Complete GitHub auth in the browser…");
    try {
      const auth = await loginWithBrowser();
      p.log.success(`Signed in as ${auth.login}`);
    } catch (err) {
      p.log.error(err instanceof Error ? err.message : String(err));
    }
  }

  const cfg = loadConfig();
  const modelAction = await p.select({
    message: "Model setup",
    options: [
      { value: "test", label: "Use current model", hint: cfg.llm.model },
      { value: "pick", label: "Pick from Ollama" },
      { value: "skip", label: "Skip" },
    ],
  });

  if (p.isCancel(modelAction)) {
    p.cancel("Setup cancelled.");
    process.exit(0);
  }

  if (modelAction === "pick") {
    const models = await listRemoteModels();
    if (!models.length) {
      p.log.warn("No Ollama models found.");
    } else {
      const chosen = await p.select({
        message: "Select model",
        options: models.map((m) => ({ value: m, label: m })),
      });
      if (!p.isCancel(chosen) && typeof chosen === "string") {
        const next = loadConfig();
        next.llm.model = chosen;
        saveConfig(next);
        p.log.success(`Active model: ${chosen}`);
      }
    }
  }

  if (modelAction !== "skip") {
    const spin = startWork("model");
    const result = await testLlmConnection();
    if (result.ok) spin.succeed(c.ok("Model ready"));
    else {
      spin.fail(c.bad("Model not reachable"));
      p.log.info("Start Ollama, then /model inside the session.");
    }
  }

  p.outro(`${c.brand("Entering Otter session")}`);
}
