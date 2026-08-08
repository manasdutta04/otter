import { getDb, nowIso, newId } from "./index.js";

export type RepositoryRow = {
  id: string;
  url: string;
  full_name: string | null;
  local_path: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export function upsertRepository(row: {
  id?: string;
  url: string;
  full_name?: string;
  local_path: string;
  status?: string;
}): RepositoryRow {
  const db = getDb();
  const id = row.id || newId("repo_");
  const ts = nowIso();
  const existing = db
    .prepare("SELECT id FROM repositories WHERE url = ? OR local_path = ?")
    .get(row.url, row.local_path) as { id: string } | undefined;

  if (existing) {
    // Never downgrade a GitHub import to a file:// stub.
    const prev = getRepository(existing.id)!;
    const nextUrl =
      row.url.startsWith("file://") && prev.url.startsWith("http") ? prev.url : row.url;
    const nextName =
      row.url.startsWith("file://") && prev.full_name?.includes("/")
        ? prev.full_name
        : (row.full_name ?? prev.full_name);
    db.prepare(
      `UPDATE repositories SET url = ?, full_name = ?, local_path = ?, status = ?, updated_at = ? WHERE id = ?`,
    ).run(
      nextUrl,
      nextName ?? null,
      row.local_path,
      row.status ?? prev.status,
      ts,
      existing.id,
    );
    return getRepository(existing.id)!;
  }

  db.prepare(
    `INSERT INTO repositories (id, url, full_name, local_path, status, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
  ).run(id, row.url, row.full_name ?? null, row.local_path, row.status ?? "pending", ts, ts);
  return getRepository(id)!;
}

export function getRepository(id: string): RepositoryRow | undefined {
  return getDb().prepare("SELECT * FROM repositories WHERE id = ?").get(id) as
    | RepositoryRow
    | undefined;
}

export function listRepositories(): RepositoryRow[] {
  return getDb()
    .prepare("SELECT * FROM repositories ORDER BY updated_at DESC")
    .all() as RepositoryRow[];
}

export function getRepositoryByPath(localPath: string): RepositoryRow | undefined {
  const normalized = localPath.replace(/\\/g, "/");
  const rows = listRepositories();
  return rows.find((r) => {
    const p = r.local_path.replace(/\\/g, "/");
    return p === normalized || p.toLowerCase() === normalized.toLowerCase();
  });
}

export function linkProject(cwd: string, repositoryId: string): void {
  getDb()
    .prepare(
      `INSERT INTO project_links (cwd, repository_id, updated_at) VALUES (?, ?, ?)
       ON CONFLICT(cwd) DO UPDATE SET repository_id = excluded.repository_id, updated_at = excluded.updated_at`,
    )
    .run(cwd, repositoryId, nowIso());
}

export function getLinkedRepoId(cwd: string): string | undefined {
  const row = getDb()
    .prepare("SELECT repository_id FROM project_links WHERE cwd = ?")
    .get(cwd) as { repository_id: string } | undefined;
  return row?.repository_id;
}

export function saveIntelligence(
  repositoryId: string,
  data: {
    summary: string;
    languages: Record<string, number>;
    tree: string[];
    raw?: unknown;
  },
): void {
  getDb()
    .prepare(
      `INSERT INTO intelligence (repository_id, summary, languages_json, tree_json, raw_json, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(repository_id) DO UPDATE SET
         summary = excluded.summary,
         languages_json = excluded.languages_json,
         tree_json = excluded.tree_json,
         raw_json = excluded.raw_json,
         updated_at = excluded.updated_at`,
    )
    .run(
      repositoryId,
      data.summary,
      JSON.stringify(data.languages),
      JSON.stringify(data.tree),
      JSON.stringify(data.raw ?? {}),
      nowIso(),
    );
  getDb()
    .prepare(`UPDATE repositories SET status = 'ready', updated_at = ? WHERE id = ?`)
    .run(nowIso(), repositoryId);
}

export function getIntelligence(repositoryId: string): {
  summary: string;
  languages: Record<string, number>;
  tree: string[];
  updated_at: string;
} | null {
  const row = getDb()
    .prepare("SELECT * FROM intelligence WHERE repository_id = ?")
    .get(repositoryId) as
    | {
        summary: string;
        languages_json: string;
        tree_json: string;
        updated_at: string;
      }
    | undefined;
  if (!row) return null;
  return {
    summary: row.summary,
    languages: JSON.parse(row.languages_json || "{}"),
    tree: JSON.parse(row.tree_json || "[]"),
    updated_at: row.updated_at,
  };
}

export function saveHealth(
  repositoryId: string,
  data: { score: number; findings: unknown[]; summary: string },
): void {
  getDb()
    .prepare(
      `INSERT INTO health_reports (repository_id, score, findings_json, summary, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(repository_id) DO UPDATE SET
         score = excluded.score,
         findings_json = excluded.findings_json,
         summary = excluded.summary,
         updated_at = excluded.updated_at`,
    )
    .run(repositoryId, data.score, JSON.stringify(data.findings), data.summary, nowIso());
}

export function getHealth(repositoryId: string): {
  score: number;
  findings: unknown[];
  summary: string;
  updated_at: string;
} | null {
  const row = getDb()
    .prepare("SELECT * FROM health_reports WHERE repository_id = ?")
    .get(repositoryId) as
    | {
        score: number;
        findings_json: string;
        summary: string;
        updated_at: string;
      }
    | undefined;
  if (!row) return null;
  return {
    score: row.score,
    findings: JSON.parse(row.findings_json || "[]"),
    summary: row.summary,
    updated_at: row.updated_at,
  };
}

export function addMemory(repositoryId: string, content: string, kind = "note"): string {
  const id = newId("mem_");
  getDb()
    .prepare(
      `INSERT INTO memory_entries (id, repository_id, kind, content, created_at) VALUES (?, ?, ?, ?, ?)`,
    )
    .run(id, repositoryId, kind, content, nowIso());
  return id;
}

export function listMemory(repositoryId: string): Array<{
  id: string;
  kind: string;
  content: string;
  created_at: string;
}> {
  return getDb()
    .prepare(
      `SELECT id, kind, content, created_at FROM memory_entries WHERE repository_id = ? ORDER BY created_at DESC`,
    )
    .all(repositoryId) as Array<{
    id: string;
    kind: string;
    content: string;
    created_at: string;
  }>;
}

export function searchMemory(
  repositoryId: string,
  query: string,
): Array<{ id: string; kind: string; content: string; created_at: string }> {
  return getDb()
    .prepare(
      `SELECT id, kind, content, created_at FROM memory_entries
       WHERE repository_id = ? AND content LIKE ?
       ORDER BY created_at DESC`,
    )
    .all(repositoryId, `%${query}%`) as Array<{
    id: string;
    kind: string;
    content: string;
    created_at: string;
  }>;
}

export function saveCodeTask(row: {
  id: string;
  repository_id: string;
  request: string;
  status: string;
  patch?: string | null;
  branch?: string | null;
  pr_url?: string | null;
}): void {
  const ts = nowIso();
  const existing = getDb().prepare("SELECT id FROM code_tasks WHERE id = ?").get(row.id);
  if (existing) {
    getDb()
      .prepare(
        `UPDATE code_tasks SET status = ?, patch = ?, branch = ?, pr_url = ?, updated_at = ? WHERE id = ?`,
      )
      .run(
        row.status,
        row.patch ?? null,
        row.branch ?? null,
        row.pr_url ?? null,
        ts,
        row.id,
      );
    return;
  }
  getDb()
    .prepare(
      `INSERT INTO code_tasks (id, repository_id, request, status, patch, branch, pr_url, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(
      row.id,
      row.repository_id,
      row.request,
      row.status,
      row.patch ?? null,
      row.branch ?? null,
      row.pr_url ?? null,
      ts,
      ts,
    );
}

export function getCodeTask(id: string): {
  id: string;
  repository_id: string;
  request: string;
  status: string;
  patch: string | null;
  branch: string | null;
  pr_url: string | null;
} | undefined {
  return getDb().prepare("SELECT * FROM code_tasks WHERE id = ?").get(id) as
    | {
        id: string;
        repository_id: string;
        request: string;
        status: string;
        patch: string | null;
        branch: string | null;
        pr_url: string | null;
      }
    | undefined;
}
