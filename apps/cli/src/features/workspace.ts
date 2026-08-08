import { chatCompletion } from "../llm/client.js";
import { readRepoContext } from "../scan/analyze.js";
import { getDb, newId, nowIso } from "../db/index.js";
import { getIntelligence, listMemory, type RepositoryRow } from "../db/repos.js";

function contextBlock(repo: RepositoryRow, root: string): string {
  const intel = getIntelligence(repo.id);
  const mem = listMemory(repo.id)
    .slice(0, 8)
    .map((m) => `- ${m.content}`)
    .join("\n");
  const files = readRepoContext(root);
  return [
    `Repository: ${repo.full_name || repo.url}`,
    `Path: ${root}`,
    intel ? `Intelligence:\n${intel.summary}` : "",
    mem ? `Memory:\n${mem}` : "",
    `Excerpts:\n${files.slice(0, 20_000)}`,
  ]
    .filter(Boolean)
    .join("\n\n");
}

export async function chatAboutRepo(
  repo: RepositoryRow,
  root: string,
  question: string,
): Promise<string> {
  const answer = await chatCompletion([
    {
      role: "system",
      content:
        "You are Otter, an engineering-intelligence assistant. Answer grounded in the repository context. Be concise and cite file paths when useful.",
    },
    {
      role: "user",
      content: `${contextBlock(repo, root)}\n\nQuestion:\n${question}`,
    },
  ]);

  const db = getDb();
  const ts = nowIso();
  db.prepare(
    `INSERT INTO chat_messages (id, repository_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)`,
  ).run(newId("chat_"), repo.id, "user", question, ts);
  db.prepare(
    `INSERT INTO chat_messages (id, repository_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)`,
  ).run(newId("chat_"), repo.id, "assistant", answer, ts);

  return answer;
}

export async function planChange(
  repo: RepositoryRow,
  root: string,
  request: string,
): Promise<{ id: string; content: string }> {
  const content = await chatCompletion([
    {
      role: "system",
      content:
        "You are Otter's planner. Produce a clear implementation plan with: goal, approach, files to touch, risks, and a short test plan. Use markdown bullets.",
    },
    {
      role: "user",
      content: `${contextBlock(repo, root)}\n\nChange request:\n${request}`,
    },
  ]);

  const id = newId("plan_");
  getDb()
    .prepare(
      `INSERT INTO plans (id, repository_id, request, content, created_at) VALUES (?, ?, ?, ?, ?)`,
    )
    .run(id, repo.id, request, content, nowIso());

  return { id, content };
}

export async function generateDocs(
  repo: RepositoryRow,
  root: string,
): Promise<{ id: string; title: string; content: string }> {
  const content = await chatCompletion([
    {
      role: "system",
      content:
        "You are Otter docs. Write a practical repository overview: purpose, stack, layout, how to run, key modules, and notable risks. Markdown.",
    },
    {
      role: "user",
      content: contextBlock(repo, root),
    },
  ]);

  const id = newId("doc_");
  const title = `Overview — ${repo.full_name || repo.id}`;
  getDb()
    .prepare(
      `INSERT INTO documents (id, repository_id, kind, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .run(id, repo.id, "overview", title, content, nowIso());

  return { id, title, content };
}

export async function reviewRepo(
  repo: RepositoryRow,
  root: string,
): Promise<{ summary: string; findings: Array<{ severity: string; message: string }> }> {
  const raw = await chatCompletion([
    {
      role: "system",
      content: `You are Otter review. Return JSON only:
{"summary":"...", "findings":[{"severity":"high|medium|low|info","message":"..."}]}
Focus on correctness, security, maintainability. Max 12 findings.`,
    },
    {
      role: "user",
      content: contextBlock(repo, root),
    },
  ]);

  let summary = raw;
  let findings: Array<{ severity: string; message: string }> = [];
  try {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");
    if (start >= 0 && end > start) {
      const parsed = JSON.parse(raw.slice(start, end + 1)) as {
        summary?: string;
        findings?: Array<{ severity: string; message: string }>;
      };
      summary = parsed.summary || raw;
      findings = parsed.findings || [];
    }
  } catch {
    findings = [{ severity: "info", message: "Could not parse structured findings; see summary." }];
  }

  getDb()
    .prepare(
      `INSERT INTO reviews (repository_id, summary, findings_json, updated_at) VALUES (?, ?, ?, ?)
       ON CONFLICT(repository_id) DO UPDATE SET summary = excluded.summary, findings_json = excluded.findings_json, updated_at = excluded.updated_at`,
    )
    .run(repo.id, summary, JSON.stringify(findings), nowIso());

  return { summary, findings };
}

export function latestPlan(repositoryId: string): { id: string; request: string; content: string } | null {
  const row = getDb()
    .prepare(
      `SELECT id, request, content FROM plans WHERE repository_id = ? ORDER BY created_at DESC LIMIT 1`,
    )
    .get(repositoryId) as { id: string; request: string; content: string } | undefined;
  return row || null;
}

export function latestDoc(repositoryId: string): { title: string; content: string } | null {
  const row = getDb()
    .prepare(
      `SELECT title, content FROM documents WHERE repository_id = ? ORDER BY created_at DESC LIMIT 1`,
    )
    .get(repositoryId) as { title: string; content: string } | undefined;
  return row || null;
}
