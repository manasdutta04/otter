import { c, pad, truncate } from "./theme.js";
import { PACKAGE_VERSION, loadConfig } from "../config.js";
import { testLlmConnection } from "../llm/client.js";

const OTTER_LOGO = [
  "██████╗ ████████╗████████╗███████╗██████╗",
  "██╔═══██╗╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗",
  "██║   ██║   ██║      ██║   █████╗  ██████╔╝",
  "██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗",
  "╚██████╔╝   ██║      ██║   ███████╗██║  ██║",
  " ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝",
];

export async function renderBanner(workspace: string): Promise<void> {
  const cfg = loadConfig();
  const cols = process.stdout.columns || 100;
  const inner = Math.min(Math.max(cols - 4, 78), 108);
  const leftW = Math.floor((inner - 3) * 0.46);
  const rightW = inner - 3 - leftW;

  let modelLine: string;
  try {
    const t = await testLlmConnection();
    modelLine = t.ok
      ? `${c.muted(cfg.llm.model)} · ${c.ok("●")} ${c.ok("Model ready")}`
      : `${c.muted(cfg.llm.model)} · ${c.bad("●")} ${c.bad("No model")}`;
  } catch {
    modelLine = `${c.bad("●")} ${c.bad("Model unreachable")}`;
  }

  const greet = cfg.auth?.login
    ? `Welcome back, ${c.brandBright(`${cfg.auth.login}!`)}`
    : `Welcome to ${c.brandBright("Otter")}`;

  const ghLine = cfg.auth?.login
    ? `${c.ok("●")} ${c.muted("GitHub connected")}`
    : `${c.accent("●")} ${c.muted("Run")} ${c.brand("/login")} ${c.muted("to connect GitHub")}`;

  const left: string[] = [
    c.text("Welcome to Otter"),
    "",
    ...OTTER_LOGO.map((line) => c.brand(line)),
    "",
    greet,
    modelLine,
    ghLine,
    c.dim(truncate(workspace.replace(/\\/g, "/"), leftW)),
  ];

  const right: string[] = [
    c.text("Getting started"),
    `${c.brand(pad("/scan", 10))} ${c.dim("Scan workspace")}`,
    `${c.brand(pad("/import", 10))} ${c.dim("Clone GitHub repo")}`,
    `${c.brand(pad("/chat", 10))} ${c.dim("Ask about the code")}`,
    `${c.brand(pad("/plan", 10))} ${c.dim("Implementation plan")}`,
    `${c.brand(pad("/create", 10))} ${c.dim("Code + optional PR")}`,
    c.dim("─".repeat(Math.min(rightW, 42))),
    c.text("Intelligence"),
    `${c.brand(pad("/intel", 10))} ${c.dim("Summary")}`,
    `${c.brand(pad("/health", 10))} ${c.dim("Health score")}`,
    `${c.brand(pad("/review", 10))} ${c.dim("Code review")}`,
    `${c.brand(pad("/docs", 10))} ${c.dim("Overview docs")}`,
    `${c.brand(pad("/pr", 10))} ${c.dim("Open pull request")}`,
    "",
    c.text("Session"),
    `${c.brand(pad("/help", 10))} ${c.dim("Full command list")}`,
    `${c.brand(pad("/exit", 10))} ${c.dim("Quit")}`,
  ];

  const n = Math.max(left.length, right.length);
  while (left.length < n) left.push("");
  while (right.length < n) right.push("");

  const topCols =
    c.border("╭") +
    c.border("─".repeat(leftW + 2)) +
    c.border("┬") +
    c.border("─".repeat(rightW + 2)) +
    c.border("╮");

  console.log();
  console.log(c.brand(`  🦦  Otter`) + c.dim(`  v${PACKAGE_VERSION}`));
  console.log(topCols);

  for (let i = 0; i < n; i++) {
    console.log(
      c.border("│") +
        " " +
        pad(truncate(left[i], leftW), leftW) +
        " " +
        c.border("│") +
        " " +
        pad(truncate(right[i], rightW), rightW) +
        " " +
        c.border("│"),
    );
  }

  console.log(
    c.border("╰") +
      c.border("─".repeat(leftW + 2)) +
      c.border("┴") +
      c.border("─".repeat(rightW + 2)) +
      c.border("╯"),
  );
  console.log(
    c.dim("  Type a task to cook with the agent · slash commands on the right"),
  );
  console.log();
}
