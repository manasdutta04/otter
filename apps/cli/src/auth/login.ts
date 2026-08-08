import http from "node:http";
import type { AddressInfo } from "node:net";
import open from "open";
import { loadConfig, saveConfig, type AuthSession } from "../config.js";

export async function loginWithBrowser(): Promise<AuthSession> {
  const cfg = loadConfig();
  const broker = cfg.brokerUrl.replace(/\/$/, "");

  if (cfg.auth?.login) {
    console.log(`Already signed in as ${cfg.auth.login}. Refreshing via browser…`);
  }

  const code = await new Promise<string>((resolve, reject) => {
    let settled = false;
    const finish = (err: Error | null, value?: string) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      // Close after a tick so the success HTML can flush to the browser.
      setTimeout(() => {
        try {
          server.close();
        } catch {
          /* ignore */
        }
      }, 250);
      if (err) reject(err);
      else resolve(value!);
    };

    const server = http.createServer((req, res) => {
      try {
        const url = new URL(req.url || "/", "http://127.0.0.1");
        if (url.pathname === "/favicon.ico") {
          res.writeHead(204);
          res.end();
          return;
        }
        if (url.pathname !== "/callback") {
          res.writeHead(404, { "Content-Type": "text/plain" });
          res.end("Otter CLI login server. Waiting for /callback.");
          return;
        }

        const redeemCode = url.searchParams.get("code");
        if (!redeemCode) {
          res.writeHead(400, { "Content-Type": "text/html; charset=utf-8" });
          res.end("<h1>Login failed</h1><p>Missing code. You can close this tab.</p>");
          finish(new Error("Missing code in callback"));
          return;
        }

        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(`<!doctype html>
<html><head><meta charset="utf-8"><title>Otter CLI</title></head>
<body style="font-family:system-ui;padding:2rem;max-width:32rem">
  <h1>Otter CLI</h1>
  <p><strong>Login complete.</strong> Return to your terminal — you can close this tab.</p>
  <script>setTimeout(() => { try { window.close(); } catch {} }, 800);</script>
</body></html>`);

        console.log("Browser callback received. Finishing login…");
        finish(null, redeemCode);
      } catch (err) {
        finish(err instanceof Error ? err : new Error(String(err)));
      }
    });

    const timer = setTimeout(() => {
      finish(new Error("Login timed out after 5 minutes. Re-run `otter login`."));
    }, 5 * 60 * 1000);

    server.on("error", (err) => finish(err));

    // Bind once (port 0) — avoid Windows race from close-then-rebind.
    server.listen(0, "127.0.0.1", async () => {
      const addr = server.address() as AddressInfo;
      const port = addr.port;
      const loginUrl = `${broker}/login?mode=cli&cli_port=${port}&return_origin=${encodeURIComponent(`http://127.0.0.1:${port}`)}`;
      console.log("Opening browser for GitHub login…");
      console.log(loginUrl);
      console.log("\nWaiting for you to finish in the browser…");
      console.log("(Terminal will continue automatically after GitHub redirects back.)\n");
      try {
        await open(loginUrl);
      } catch {
        console.log("Could not open a browser automatically — paste the URL above into one.");
      }
    });
  });

  const redeemRes = await fetch(`${broker}/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, mode: "cli" }),
  });
  if (!redeemRes.ok) {
    const text = await redeemRes.text();
    throw new Error(`Broker redeem failed: ${text}`);
  }
  const payload = (await redeemRes.json()) as {
    access_token: string;
    github_user: { id: number; login: string; avatar_url?: string };
    installation_id?: number | null;
  };

  const auth: AuthSession = {
    accessToken: payload.access_token,
    login: payload.github_user.login,
    userId: payload.github_user.id,
    avatarUrl: payload.github_user.avatar_url,
    installationId: payload.installation_id ?? null,
    expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  };

  const next = loadConfig();
  next.auth = auth;
  saveConfig(next);
  return auth;
}
