#!/usr/bin/env node
/**
 * Otter CLI — interactive-first (Claude Code–style session).
 * Primary UX: run `otter` with no args.
 */
import { Command } from "commander";
import chalk from "chalk";
import { PACKAGE_VERSION } from "./config.js";
import { launchInteractive } from "./tui/app.js";

const program = new Command();

program
  .name("otter")
  .description("Otter — interactive engineering intelligence")
  .version(PACKAGE_VERSION, "-V, --version")
  .option("--path <dir>", "workspace directory")
  .option("--skip-setup", "skip splash onboarding menus")
  .action(async (opts: { path?: string; skipSetup?: boolean }) => {
    await launchInteractive({ path: opts.path, skipOnboarding: opts.skipSetup });
  });

// Hidden escape hatch for scripts / CI — not shown as the product surface.
program
  .command("run", { hidden: true })
  .argument("<prompt...>")
  .option("--path <dir>")
  .option("--yes")
  .action(async (promptParts: string[], opts: { path?: string; yes?: boolean }) => {
    const { resolveWorkRoot } = await import("./git/repos.js");
    const { runAgent } = await import("./agent/loop.js");
    const { root } = resolveWorkRoot(opts.path);
    await runAgent(promptParts.join(" "), { root, autoApprove: Boolean(opts.yes) });
  });

async function main(): Promise<void> {
  try {
    await program.parseAsync(process.argv);
  } catch (err) {
    console.error(chalk.red(err instanceof Error ? err.message : String(err)));
    process.exit(1);
  }
}

main();
