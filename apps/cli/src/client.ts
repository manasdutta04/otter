import { homedir } from "node:os";
import { join } from "node:path";
import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { createServer } from "node:http";
import { spawn } from "node:child_process";

export type OtterConfig = {
  apiUrl: string;
  session?: string;
};

const CONFIG_DIR = join(homedir(), ".otter");
const CONFIG_PATH = join(CONFIG_DIR, "config.json");

export function loadConfig(): OtterConfig {
  const defaults: OtterConfig = {
    apiUrl: process.env.OTTER_API_URL ?? "http://localhost:8000",
    session: process.env.OTTER_SESSION,
  };
  if (!existsSync(CONFIG_PATH)) return defaults;
  try {
    const parsed = JSON.parse(readFileSync(CONFIG_PATH, "utf8")) as Partial<OtterConfig>;
    return {
      apiUrl: parsed.apiUrl ?? defaults.apiUrl,
      session: process.env.OTTER_SESSION ?? parsed.session ?? defaults.session,
    };
  } catch {
    return defaults;
  }
}

export function saveConfig(config: OtterConfig): void {
  mkdirSync(CONFIG_DIR, { recursive: true });
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), "utf8");
}

export function clearSession(): void {
  const config = loadConfig();
  delete config.session;
  saveConfig(config);
  if (existsSync(CONFIG_PATH) && !config.session) {
    // keep apiUrl
  }
}

export async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const config = loadConfig();
  if (!config.session && !path.startsWith("/health") && !path.startsWith("/auth/")) {
    throw new Error("Not logged in. Run `otter login` first.");
  }
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (config.session) {
    headers.Cookie = `otter_session=${config.session}`;
    headers["X-Otter-Session"] = config.session;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${config.apiUrl.replace(/\/$/, "")}${path}`, {
    method: options.method ?? (options.body ? "POST" : "GET"),
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Otter API ${response.status}: ${text}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function openBrowser(url: string): void {
  const platform = process.platform;
  if (platform === "win32") {
    spawn("cmd", ["/c", "start", "", url], { detached: true, stdio: "ignore" }).unref();
  } else if (platform === "darwin") {
    spawn("open", [url], { detached: true, stdio: "ignore" }).unref();
  } else {
    spawn("xdg-open", [url], { detached: true, stdio: "ignore" }).unref();
  }
}

export async function loginWithBrowser(): Promise<string> {
  const config = loadConfig();
  return await new Promise<string>((resolve, reject) => {
    const server = createServer((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      if (url.pathname !== "/callback") {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const session = url.searchParams.get("session");
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end("<html><body><h1>🦦 Otter login complete</h1><p>You can close this window.</p></body></html>");
      server.close();
      if (!session) {
        reject(new Error("Login callback missing session"));
        return;
      }
      resolve(session);
    });
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("Failed to bind local login callback"));
        return;
      }
      const loginUrl = `${config.apiUrl.replace(/\/$/, "")}/auth/github/login?cli_port=${address.port}`;
      console.error(`Opening browser for Otter login…\n${loginUrl}`);
      openBrowser(loginUrl);
    });
    server.on("error", reject);
    setTimeout(() => {
      server.close();
      reject(new Error("Login timed out after 5 minutes"));
    }, 5 * 60 * 1000);
  });
}

export function printJson(data: unknown): void {
  console.log(JSON.stringify(data, null, 2));
}

export { CONFIG_PATH, unlinkSync };
