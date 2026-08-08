import Database from "better-sqlite3";
import { globalDbPath } from "../config.js";

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (db) return db;
  db = new Database(globalDbPath());
  db.pragma("journal_mode = WAL");
  migrate(db);
  return db;
}

function migrate(database: Database.Database): void {
  database.exec(`
    CREATE TABLE IF NOT EXISTS repositories (
      id TEXT PRIMARY KEY,
      url TEXT NOT NULL,
      full_name TEXT,
      local_path TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS intelligence (
      repository_id TEXT PRIMARY KEY,
      summary TEXT,
      languages_json TEXT,
      tree_json TEXT,
      raw_json TEXT,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS health_reports (
      repository_id TEXT PRIMARY KEY,
      score INTEGER,
      findings_json TEXT,
      summary TEXT,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS memory_entries (
      id TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      kind TEXT NOT NULL DEFAULT 'note',
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS code_tasks (
      id TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      request TEXT NOT NULL,
      status TEXT NOT NULL,
      patch TEXT,
      branch TEXT,
      pr_url TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS project_links (
      cwd TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS plans (
      id TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      request TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
      repository_id TEXT PRIMARY KEY,
      summary TEXT NOT NULL,
      findings_json TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      kind TEXT NOT NULL DEFAULT 'overview',
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
      id TEXT PRIMARY KEY,
      repository_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (repository_id) REFERENCES repositories(id)
    );
  `);
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function newId(prefix = ""): string {
  const id = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  return prefix ? `${prefix}${id}` : id;
}
