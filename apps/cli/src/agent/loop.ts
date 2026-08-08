import readline from "node:readline";
import type OpenAI from "openai";
import chalk from "chalk";
import { createLlmClient } from "../llm/client.js";
import { loadConfig } from "../config.js";
import { TOOL_SPECS, runTool, type ToolName } from "./tools.js";
import { readRepoContext } from "../scan/analyze.js";

const TOOL_NAMES = new Set(TOOL_SPECS.map((t) => t.function.name));

const SYSTEM = `You are Otter, a local engineering-intelligence coding agent.
You work inside a single workspace directory. Prefer small, correct changes.

You have tools: read, write, edit, bash, glob, grep.

When you need a tool, emit one or more JSON objects (no markdown fences), each on its own line or block:
{"name":"read","arguments":{"path":"server/routes.ts"}}
{"name":"write","arguments":{"path":"server/routes/health.ts","content":"..."}}
{"name":"edit","arguments":{"path":"file.ts","old_string":"...","new_string":"..."}}

After tools run you will receive results. Then continue or finish with a short summary.
Do not pretend tools ran — only emit the JSON and wait.`;

export type AgentOptions = {
  root: string;
  autoApprove?: boolean;
  maxTurns?: number;
  onEvent?: (msg: string) => void;
};

type ParsedCall = { name: ToolName; arguments: Record<string, string>; id: string };

async function confirm(prompt: string): Promise<boolean> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const answer = await new Promise<string>((resolve) => {
    rl.question(`${prompt} [y/N] `, resolve);
  });
  rl.close();
  return /^y(es)?$/i.test(answer.trim());
}

/** Extract tool JSON from model prose (Ollama often won't use native tool_calls). */
export function extractToolCallsFromText(text: string): ParsedCall[] {
  if (!text) return [];
  const calls: ParsedCall[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < text.length; i++) {
    if (text[i] !== "{") continue;
    if (!text.slice(i, i + 40).includes('"name"')) continue;
    let depth = 0;
    let end = -1;
    let inStr = false;
    let esc = false;
    for (let j = i; j < text.length; j++) {
      const ch = text[j];
      if (inStr) {
        if (esc) esc = false;
        else if (ch === "\\") esc = true;
        else if (ch === '"') inStr = false;
        continue;
      }
      if (ch === '"') inStr = true;
      else if (ch === "{") depth++;
      else if (ch === "}") {
        depth--;
        if (depth === 0) {
          end = j;
          break;
        }
      }
    }
    if (end < 0) continue;
    const slice = text.slice(i, end + 1);
    i = end;
    try {
      const obj = JSON.parse(slice) as { name?: string; arguments?: Record<string, string> };
      if (!obj.name || !TOOL_NAMES.has(obj.name)) continue;
      const args = obj.arguments || {};
      const key = `${obj.name}:${JSON.stringify(args)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      calls.push({
        name: obj.name as ToolName,
        arguments: args,
        id: `text_${calls.length + 1}`,
      });
    } catch {
      /* skip */
    }
  }
  return calls;
}

function nativeToolCalls(
  toolCalls: OpenAI.Chat.ChatCompletionMessageToolCall[] | undefined,
): ParsedCall[] {
  if (!toolCalls?.length) return [];
  const out: ParsedCall[] = [];
  for (const tc of toolCalls) {
    if (tc.type !== "function") continue;
    let args: Record<string, string> = {};
    try {
      args = JSON.parse(tc.function.arguments || "{}") as Record<string, string>;
    } catch {
      args = {};
    }
    out.push({ name: tc.function.name as ToolName, arguments: args, id: tc.id });
  }
  return out;
}

async function executeCalls(
  root: string,
  calls: ParsedCall[],
  opts: AgentOptions,
  log: (m: string) => void,
): Promise<Array<{ id: string; result: string }>> {
  const results: Array<{ id: string; result: string }> = [];
  for (const call of calls) {
    log(chalk.dim(`→ ${call.name} ${JSON.stringify(call.arguments).slice(0, 200)}`));
    const needsWrite = call.name === "write" || call.name === "edit" || call.name === "bash";
    if (needsWrite && !opts.autoApprove) {
      const ok = await confirm(`Allow ${call.name}?`);
      if (!ok) {
        results.push({ id: call.id, result: "User rejected this tool call." });
        continue;
      }
    }
    try {
      const result = runTool(root, { name: call.name, arguments: call.arguments }, { allowWrite: true });
      results.push({ id: call.id, result: result.slice(0, 40_000) });
    } catch (err) {
      results.push({
        id: call.id,
        result: `Error: ${err instanceof Error ? err.message : String(err)}`,
      });
    }
  }
  return results;
}

export async function runAgent(prompt: string, opts: AgentOptions): Promise<string> {
  const cfg = loadConfig();
  const client = createLlmClient();
  const log = opts.onEvent || ((m: string) => console.log(m));
  const context = readRepoContext(opts.root);
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM },
    {
      role: "user",
      content: `Workspace: ${opts.root}\n\nContext excerpts:\n${context.slice(0, 24_000)}\n\nTask:\n${prompt}`,
    },
  ];

  let finalText = "";
  const maxTurns = opts.maxTurns ?? 12;
  let useNativeTools = true;

  for (let turn = 0; turn < maxTurns; turn++) {
    let content = "";
    let nativeCalls: ParsedCall[] = [];

    if (useNativeTools) {
      try {
        const res = await client.chat.completions.create({
          model: cfg.llm.model,
          messages,
          tools: TOOL_SPECS,
          tool_choice: "auto",
          temperature: 0.2,
        });
        const msg = res.choices[0]?.message;
        if (!msg) break;
        content = msg.content?.trim() || "";
        nativeCalls = nativeToolCalls(msg.tool_calls);
        if (content) {
          log(chalk.cyan(content));
          finalText = content;
        }
      } catch {
        useNativeTools = false;
      }
    }

    if (!useNativeTools) {
      const plain = await client.chat.completions.create({
        model: cfg.llm.model,
        messages,
        temperature: 0.2,
      });
      content = plain.choices[0]?.message?.content?.trim() || "";
      if (content) {
        log(chalk.cyan(content));
        finalText = content;
      }
    }

    const textCalls = extractToolCallsFromText(content);
    const calls = nativeCalls.length ? nativeCalls : textCalls;

    if (!calls.length) {
      break;
    }

    if (nativeCalls.length && useNativeTools) {
      messages.push({
        role: "assistant",
        content: content || null,
        tool_calls: nativeCalls.map((c) => ({
          id: c.id,
          type: "function" as const,
          function: { name: c.name, arguments: JSON.stringify(c.arguments) },
        })),
      });
      const results = await executeCalls(opts.root, calls, opts, log);
      for (const r of results) {
        messages.push({ role: "tool", tool_call_id: r.id, content: r.result });
      }
    } else {
      // Text-protocol path for local models
      messages.push({ role: "assistant", content });
      const results = await executeCalls(opts.root, calls, opts, log);
      const report = results
        .map((r, i) => `Tool ${calls[i].name} result:\n${r.result}`)
        .join("\n\n");
      messages.push({
        role: "user",
        content: `${report}\n\nContinue. Emit more tool JSON if needed, or finish with a short summary.`,
      });
    }
  }

  return finalText;
}

export async function startRepl(root: string): Promise<void> {
  console.log(chalk.bold("\n🦦 Otter"));
  console.log(chalk.dim(`Workspace: ${root}`));
  console.log(chalk.dim("Type a task, or /help /scan /model /login /clear /exit\n"));

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: chalk.green("otter> "),
  });

  rl.prompt();
  rl.on("line", async (line) => {
    const input = line.trim();
    if (!input) {
      rl.prompt();
      return;
    }

    try {
      if (input === "/exit" || input === "/quit") {
        rl.close();
        return;
      }
      if (input === "/help") {
        console.log(`Commands:
  /help     this help
  /scan     scan workspace
  /model    show active model
  /login    GitHub login
  /logout   clear session
  /clear    clear screen
  /exit     quit
Or type any coding / intelligence request.`);
        rl.prompt();
        return;
      }
      if (input === "/clear") {
        console.clear();
        rl.prompt();
        return;
      }
      if (input === "/model") {
        const cfg = loadConfig();
        console.log(`${cfg.llm.model} @ ${cfg.llm.baseUrl}`);
        rl.prompt();
        return;
      }
      if (input === "/login") {
        const { loginWithBrowser } = await import("../auth/login.js");
        const auth = await loginWithBrowser();
        console.log(`Logged in as ${auth.login}`);
        rl.prompt();
        return;
      }
      if (input === "/logout") {
        const { clearAuth } = await import("../config.js");
        clearAuth();
        console.log("Logged out.");
        rl.prompt();
        return;
      }
      if (input === "/scan") {
        const { ensureProjectRepo } = await import("../git/repos.js");
        const { scanRepository } = await import("../scan/analyze.js");
        const repo = ensureProjectRepo(root);
        const result = await scanRepository(repo.id, root);
        console.log(result.summary);
        console.log(result.health.summary);
        rl.prompt();
        return;
      }

      await runAgent(input, { root });
    } catch (err) {
      console.error(chalk.red(err instanceof Error ? err.message : String(err)));
    }
    rl.prompt();
  });

  await new Promise<void>((resolve) => rl.on("close", resolve));
}
