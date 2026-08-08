import { runOnboarding } from "./onboarding.js";
import { startSession } from "./session.js";
import { c } from "./theme.js";
import { loadConfig } from "../config.js";

export async function launchInteractive(opts?: { path?: string; skipOnboarding?: boolean }): Promise<void> {
  if (!process.stdout.isTTY) {
    console.error(c.bad("Otter needs an interactive terminal. Open a normal terminal and run `otter`."));
    process.exit(1);
  }

  console.clear();

  const cfg = loadConfig();
  const forceSetup = process.argv.includes("--setup");
  if (!opts?.skipOnboarding && (forceSetup || !cfg.auth?.accessToken)) {
    await runOnboarding();
    console.clear();
  }

  await startSession(opts?.path);
}
