import OpenAI from "openai";
import { loadConfig, type LlmConfig } from "../config.js";

export function createLlmClient(overrides?: Partial<LlmConfig>): OpenAI {
  const llm = { ...loadConfig().llm, ...overrides };
  return new OpenAI({
    apiKey: llm.apiKey || "ollama",
    baseURL: llm.baseUrl,
  });
}

export async function chatCompletion(
  messages: OpenAI.Chat.ChatCompletionMessageParam[],
  opts?: { model?: string; temperature?: number },
): Promise<string> {
  const cfg = loadConfig().llm;
  const client = createLlmClient();
  const res = await client.chat.completions.create({
    model: opts?.model || cfg.model,
    messages,
    temperature: opts?.temperature ?? 0.2,
  });
  return res.choices[0]?.message?.content?.trim() || "";
}

export async function listRemoteModels(): Promise<string[]> {
  const cfg = loadConfig().llm;
  const base = cfg.baseUrl.replace(/\/v1\/?$/, "");
  try {
    const res = await fetch(`${base}/api/tags`);
    if (res.ok) {
      const data = (await res.json()) as { models?: Array<{ name: string }> };
      return (data.models || []).map((m) => m.name);
    }
  } catch {
    /* fall through */
  }
  try {
    const client = createLlmClient();
    const models = await client.models.list();
    const names: string[] = [];
    for await (const m of models) {
      names.push(m.id);
    }
    return names;
  } catch {
    return [];
  }
}

export async function testLlmConnection(): Promise<{ ok: boolean; detail: string }> {
  try {
    const reply = await chatCompletion(
      [{ role: "user", content: "Reply with exactly: ok" }],
      { temperature: 0 },
    );
    return { ok: true, detail: reply.slice(0, 200) };
  } catch (err) {
    return { ok: false, detail: err instanceof Error ? err.message : String(err) };
  }
}
