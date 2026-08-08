import type OpenAI from "openai";
import chalk from "chalk";
import { createLlmClient } from "../llm/client.js";
import { loadConfig } from "../config.js";
import { TOOL_SPECS, runTool, type ToolName } from "./tools.js";
import { readRepoContext } from "../scan/analyze.js";
import { confirmYn } from "../tui/prompt.js";

const TOOL_NAMES = new Set(TOOL_SPECS.map((t) => t.function.name));

const SYSTEM = `You are Otter, a local engineering-intelligence coding agent.
You work inside a single workspace directory. Prefer small, correct changes.

ALWAYS inspect the real layout first with glob/read (e.g. server/routes.ts, package.json).
Do NOT invent paths like src/server unless they exist.

Tools: read, write, edit, bash, glob, grep.

When you need a tool, emit ONLY valid JSON (double quotes everywhere, never \\'):
{"name":"read","arguments":{"path":"server/routes.ts"}}
{"name":"write","arguments":{"path":"server/routes/health.ts","content":"..."}}
{"name":"edit","arguments":{"path":"server/routes.ts","old_string":"...","new_string":"..."}}

After tools run you receive results. Then continue or finish with a short summary.
Do not pretend tools ran — only emit the JSON and wait.`;

export type AgentOptions = {
  root: string;
  autoApprove?: boolean;
  maxTurns?: number;
  onEvent?: (msg: string) => void;
};

type ParsedCall = { name: ToolName; arguments: Record<string, string>; id: string };

async function confirm(prompt: string): Promise<boolean> {
  return confirmYn(prompt, false);
}

/** Ollama often emits invalid JSON (\\' instead of '). */
function repairToolJson(raw: string): string {
  return raw.replace(/\\'/g, "'");
}

function parseToolObject(slice: string): ParsedCall | null {
  for (const candidate of [slice, repairToolJson(slice)]) {
    try {
      const obj = JSON.parse(candidate) as {
        name?: string;
        arguments?: Record<string, string> | string;
      };
      if (!obj.name || !TOOL_NAMES.has(obj.name)) return null;
      let args: Record<string, string> = {};
      if (typeof obj.arguments === "string") {
        try {
          args = JSON.parse(repairToolJson(obj.arguments)) as Record<string, string>;
        } catch {
          args = {};
        }
      } else if (obj.arguments && typeof obj.arguments === "object") {
        args = obj.arguments as Record<string, string>;
      }
      // Coerce all values to strings for tool runner
      const normalized: Record<string, string> = {};
      for (const [k, v] of Object.entries(args)) {
        normalized[k] = typeof v === "string" ? v : JSON.stringify(v);
      }
      return {
        name: obj.name as ToolName,
        arguments: normalized,
        id: `text_tmp`,
      };
    } catch {
      /* next */
    }
  }
  return null;
}

/** Extract tool JSON from model prose (Ollama often won't use native tool_calls). */
export function extractToolCallsFromText(text: string): ParsedCall[] {
  if (!text) return [];
  const calls: ParsedCall[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < text.length; i++) {
    if (text[i] !== "{") continue;
    if (!text.slice(i, i + 80).includes('"name"')) continue;
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
    const parsed = parseToolObject(slice);
    if (!parsed) continue;
    const key = `${parsed.name}:${JSON.stringify(parsed.arguments)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    parsed.id = `text_${calls.length + 1}`;
    calls.push(parsed);
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
      args = JSON.parse(repairToolJson(tc.function.arguments || "{}")) as Record<string, string>;
    } catch {
      args = {};
    }
    const normalized: Record<string, string> = {};
    for (const [k, v] of Object.entries(args)) {
      normalized[k] = typeof v === "string" ? v : JSON.stringify(v);
    }
    out.push({ name: tc.function.name as ToolName, arguments: normalized, id: tc.id });
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
  let writes = 0;

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

    for (const call of calls) {
      if (call.name === "write" || call.name === "edit") writes++;
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
      messages.push({ role: "assistant", content });
      const results = await executeCalls(opts.root, calls, opts, log);
      const report = results
        .map((r, i) => `Tool ${calls[i].name} result:\n${r.result}`)
        .join("\n\n");
      messages.push({
        role: "user",
        content: `${report}\n\nContinue. Emit more tool JSON if needed (valid JSON only), or finish with a short summary.`,
      });
    }
  }

  return finalText;
}
