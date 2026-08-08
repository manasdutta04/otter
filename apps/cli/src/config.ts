import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
export const PACKAGE_VERSION = String(
  (require("../package.json") as { version?: string }).version || "0.0.0",
);
export const DEFAULT_BROKER_URL =
  "https://otter-auth-broker.manasdutta512.workers.dev";
export const DEFAULT_LLM_BASE_URL = "http://127.0.0.1:11434/v1";
export const DEFAULT_LLM_MODEL = "qwen2.5-coder:7b";
export const SITE_URL = "https://otter.manasdutta.com";
export const SUPPORT_URL = "https://github.com/manasdutta04/otter/issues";

export type LlmConfig = {
  baseUrl: string;
  model: string;
  apiKey: string;
  provider: "ollama" | "openai_compatible";
};

export type AuthSession = {
  accessToken: string;
  login: string;
  userId: number;
  avatarUrl?: string;
  installationId?: number | null;
  expiresAt?: string;
};

export type OtterConfig = {
  brokerUrl: string;
  auth?: AuthSession;
  llm: LlmConfig;
  activeRepoId?: string;
};

function homeOtterDir(): string {
  return path.join(os.homedir(), ".otter");
}

export function otterHome(): string {
  const dir = homeOtterDir();
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function configPath(): string {
  return path.join(otterHome(), "config.json");
}

export function globalDbPath(): string {
  return path.join(otterHome(), "otter.db");
}

export function reposRoot(): string {
  const dir = path.join(otterHome(), "repos");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function projectOtterDir(cwd = process.cwd()): string {
  const dir = path.join(cwd, ".otter");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function defaultConfig(): OtterConfig {
  return {
    brokerUrl: process.env.OTTER_AUTH_BROKER_URL || DEFAULT_BROKER_URL,
    llm: {
      baseUrl: process.env.OTTER_LLM_BASE_URL || DEFAULT_LLM_BASE_URL,
      model: process.env.OTTER_LLM_MODEL || DEFAULT_LLM_MODEL,
      apiKey: process.env.OTTER_LLM_API_KEY || "ollama",
      provider: "ollama",
    },
  };
}

type LegacyConfig = Partial<OtterConfig> & {
  llmBaseUrl?: string;
  llmModel?: string;
  githubAccessToken?: string;
  githubUser?: { id?: number; login?: string; avatar_url?: string };
  installationId?: number | null;
};

function migrateLegacy(raw: LegacyConfig, base: OtterConfig): OtterConfig {
  const llm = {
    ...base.llm,
    ...(raw.llm || {}),
    baseUrl: raw.llm?.baseUrl || raw.llmBaseUrl || base.llm.baseUrl,
    model: raw.llm?.model || raw.llmModel || base.llm.model,
  };

  let auth = raw.auth;
  if (!auth?.accessToken && raw.githubAccessToken) {
    auth = {
      accessToken: raw.githubAccessToken,
      login: raw.githubUser?.login || "unknown",
      userId: raw.githubUser?.id || 0,
      avatarUrl: raw.githubUser?.avatar_url,
      installationId: raw.installationId ?? null,
    };
  }

  return {
    brokerUrl: raw.brokerUrl || base.brokerUrl,
    llm,
    auth,
    activeRepoId: raw.activeRepoId,
  };
}

export function loadConfig(): OtterConfig {
  const p = configPath();
  if (!fs.existsSync(p)) {
    const cfg = defaultConfig();
    saveConfig(cfg);
    return cfg;
  }
  try {
    const raw = JSON.parse(fs.readFileSync(p, "utf8")) as LegacyConfig;
    const base = defaultConfig();
    const cfg = migrateLegacy(raw, base);
    // Persist migrated shape once so later reads stay clean.
    if (raw.githubAccessToken || raw.llmBaseUrl || raw.llmModel) {
      saveConfig(cfg);
    }
    return cfg;
  } catch {
    return defaultConfig();
  }
}

export function saveConfig(cfg: OtterConfig): void {
  fs.writeFileSync(configPath(), JSON.stringify(cfg, null, 2), "utf8");
}

export function clearAuth(): void {
  const cfg = loadConfig();
  delete cfg.auth;
  saveConfig(cfg);
  // Also strip any leftover legacy keys if file was hand-edited.
  try {
    const p = configPath();
    const raw = JSON.parse(fs.readFileSync(p, "utf8")) as Record<string, unknown>;
    delete raw.githubAccessToken;
    delete raw.githubUser;
    delete raw.installationId;
    fs.writeFileSync(p, JSON.stringify({ ...raw, ...cfg, auth: undefined }, null, 2), "utf8");
    saveConfig(cfg);
  } catch {
    /* ignore */
  }
}

export function requireAuth(): AuthSession {
  const auth = loadConfig().auth;
  if (!auth?.accessToken) {
    throw new Error("Not logged in. Run `otter login` first.");
  }
  return auth;
}
