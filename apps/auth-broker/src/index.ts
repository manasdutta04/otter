/**
 * Otter auth broker — Cloudflare Worker.
 * Holds GitHub App secrets; completes OAuth; hands a one-time code to local Otter.
 */

export interface Env {
  AUTH_KV: KVNamespace;
  /** OAuth App Client ID (what you have today) or GitHub App Client ID */
  GITHUB_APP_CLIENT_ID: string;
  GITHUB_APP_CLIENT_SECRET: string;
  /** Optional. Only for GitHub Apps install URL. Leave unset for OAuth App. */
  GITHUB_APP_SLUG?: string;
  REDEEM_HMAC_SECRET?: string;
  GITHUB_APP_ID?: string;
  GITHUB_APP_PRIVATE_KEY?: string;
  ALLOWED_RETURN_ORIGINS?: string;
  /** Comma scopes for OAuth App authorize. Default: read:user repo */
  GITHUB_OAUTH_SCOPES?: string;
}

type LoginState = {
  return_origin: string;
  cli_port?: number;
  /** cli = standalone otter-engg; api = Docker/local API */
  mode?: "cli" | "api";
  installation_id?: number;
  setup_action?: string | null;
  created_at: number;
};

type RedeemPayload = {
  access_token: string;
  token_type?: string;
  scope?: string;
  github_user: {
    id: number;
    login: string;
    avatar_url?: string;
  };
  installation_id?: number;
  created_at: number;
  mode?: "cli" | "api";
};

const STATE_TTL = 600; // 10 minutes
const REDEEM_TTL = 120; // 2 minutes

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function bad(message: string, status = 400): Response {
  return json({ error: message }, status);
}

function allowedOrigins(env: Env): string[] {
  const raw =
    env.ALLOWED_RETURN_ORIGINS ||
    "http://127.0.0.1:8000,http://localhost:8000";
  return raw
    .split(",")
    .map((s) => s.trim().replace(/\/$/, ""))
    .filter(Boolean);
}

function isAllowedReturnOrigin(origin: string, env: Env): boolean {
  const normalized = origin.replace(/\/$/, "");
  if (allowedOrigins(env).includes(normalized)) return true;
  // Allow any 127.0.0.1 / localhost with explicit port for CLI loopback redeem via API only
  try {
    const u = new URL(normalized);
    if (u.protocol !== "http:") return false;
    return u.hostname === "127.0.0.1" || u.hostname === "localhost";
  } catch {
    return false;
  }
}

function randomId(bytes = 24): string {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return [...arr].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function workerOrigin(request: Request): string {
  const url = new URL(request.url);
  return `${url.protocol}//${url.host}`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/$/, "") || "/";

    if (request.method === "GET" && path === "/") {
      return json({
        service: "otter-auth-broker",
        ok: true,
        login: "/login",
        redeem: "POST /redeem",
      });
    }

    if (request.method === "GET" && path === "/login") {
      return handleLogin(request, env, url);
    }

    if (request.method === "GET" && path === "/callback") {
      return handleCallback(request, env, url);
    }

    if (request.method === "POST" && path === "/redeem") {
      return handleRedeem(request, env);
    }

    return bad("Not found", 404);
  },
};

async function handleLogin(request: Request, env: Env, url: URL): Promise<Response> {
  if (!env.GITHUB_APP_CLIENT_ID || !env.GITHUB_APP_CLIENT_SECRET) {
    return bad("Broker is not configured (missing GITHUB_APP_CLIENT_ID / SECRET)", 503);
  }

  const modeParam = (url.searchParams.get("mode") || "").toLowerCase();
  const mode: "cli" | "api" = modeParam === "cli" ? "cli" : "api";

  let cliPort: number | undefined;
  const cliRaw = url.searchParams.get("cli_port");
  if (cliRaw) {
    cliPort = Number(cliRaw);
    if (!Number.isInteger(cliPort) || cliPort < 1024 || cliPort > 65535) {
      return bad("Invalid cli_port");
    }
  }

  let returnOrigin = (url.searchParams.get("return_origin") || "").replace(/\/$/, "");
  if (mode === "cli") {
    if (!cliPort) {
      return bad("CLI login requires cli_port");
    }
    if (!returnOrigin) {
      returnOrigin = `http://127.0.0.1:${cliPort}`;
    }
  }

  if (!returnOrigin || !isAllowedReturnOrigin(returnOrigin, env)) {
    return bad("Invalid or missing return_origin (must be local Otter API origin)");
  }

  const state = randomId(16);
  const loginState: LoginState = {
    return_origin: returnOrigin,
    cli_port: cliPort,
    mode,
    created_at: Date.now(),
  };
  await env.AUTH_KV.put(`state:${state}`, JSON.stringify(loginState), {
    expirationTtl: STATE_TTL,
  });

  // GitHub App path (optional): install URL when slug is configured.
  if (env.GITHUB_APP_SLUG) {
    const install = new URL(`https://github.com/apps/${env.GITHUB_APP_SLUG}/installations/new`);
    install.searchParams.set("state", state);
    return Response.redirect(install.toString(), 302);
  }

  // Default: classic OAuth App authorize (what Otter already has).
  const authorize = new URL("https://github.com/login/oauth/authorize");
  authorize.searchParams.set("client_id", env.GITHUB_APP_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", `${workerOrigin(request)}/callback`);
  authorize.searchParams.set("scope", env.GITHUB_OAUTH_SCOPES || "read:user repo");
  authorize.searchParams.set("state", state);
  return Response.redirect(authorize.toString(), 302);
}

async function handleCallback(request: Request, env: Env, url: URL): Promise<Response> {
  if (!env.GITHUB_APP_CLIENT_ID || !env.GITHUB_APP_CLIENT_SECRET) {
    return bad("Broker is not configured", 503);
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const setupAction = url.searchParams.get("setup_action");
  const installationIdRaw = url.searchParams.get("installation_id");

  if (!state) {
    return bad("Missing state");
  }

  const rawState = await env.AUTH_KV.get(`state:${state}`);
  if (!rawState) {
    return bad("Unknown or expired state", 400);
  }
  await env.AUTH_KV.delete(`state:${state}`);
  const loginState = JSON.parse(rawState) as LoginState;

  // Installation-only redirect without code — send user through OAuth authorize.
  if (!code) {
    const authorize = new URL("https://github.com/login/oauth/authorize");
    authorize.searchParams.set("client_id", env.GITHUB_APP_CLIENT_ID);
    authorize.searchParams.set("redirect_uri", `${workerOrigin(request)}/callback`);
    const resumeState = randomId(16);
    await env.AUTH_KV.put(
      `state:${resumeState}`,
      JSON.stringify({
        ...loginState,
        installation_id: installationIdRaw ? Number(installationIdRaw) : loginState.installation_id,
        setup_action: setupAction,
      } satisfies LoginState),
      { expirationTtl: STATE_TTL },
    );
    authorize.searchParams.set("state", resumeState);
    return Response.redirect(authorize.toString(), 302);
  }

  const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      client_id: env.GITHUB_APP_CLIENT_ID,
      client_secret: env.GITHUB_APP_CLIENT_SECRET,
      code,
      redirect_uri: `${workerOrigin(request)}/callback`,
    }),
  });
  const tokenJson = (await tokenRes.json()) as {
    access_token?: string;
    token_type?: string;
    scope?: string;
    error?: string;
    error_description?: string;
  };
  if (!tokenJson.access_token) {
    return bad(tokenJson.error_description || tokenJson.error || "Token exchange failed", 400);
  }

  const userRes = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${tokenJson.access_token}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "otter-auth-broker",
    },
  });
  if (!userRes.ok) {
    return bad("Failed to fetch GitHub user", 502);
  }
  const githubUser = (await userRes.json()) as {
    id: number;
    login: string;
    avatar_url?: string;
  };

  let installationId: number | undefined = installationIdRaw
    ? Number(installationIdRaw)
    : loginState.installation_id;

  if (!installationId) {
    const instRes = await fetch("https://api.github.com/user/installations", {
      headers: {
        Authorization: `Bearer ${tokenJson.access_token}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "otter-auth-broker",
      },
    });
    if (instRes.ok) {
      const instJson = (await instRes.json()) as {
        installations?: Array<{ id: number; app_slug?: string }>;
      };
      const match = (instJson.installations || []).find(
        (i) => !env.GITHUB_APP_SLUG || i.app_slug === env.GITHUB_APP_SLUG,
      );
      installationId = match?.id ?? instJson.installations?.[0]?.id;
    }
  }

  const redeemCode = randomId(24);
  const payload: RedeemPayload = {
    access_token: tokenJson.access_token,
    token_type: tokenJson.token_type,
    scope: tokenJson.scope,
    github_user: {
      id: githubUser.id,
      login: githubUser.login,
      avatar_url: githubUser.avatar_url,
    },
    installation_id: installationId,
    created_at: Date.now(),
    mode: loginState.mode || "api",
  };
  await env.AUTH_KV.put(`redeem:${redeemCode}`, JSON.stringify(payload), {
    expirationTtl: REDEEM_TTL,
  });

  // Standalone CLI: redirect straight to loopback callback (no Docker API).
  if (loginState.mode === "cli" && loginState.cli_port) {
    const dest = new URL(`http://127.0.0.1:${loginState.cli_port}/callback`);
    dest.searchParams.set("code", redeemCode);
    return Response.redirect(dest.toString(), 302);
  }

  const dest = new URL(`${loginState.return_origin}/auth/github/broker/callback`);
  dest.searchParams.set("code", redeemCode);
  if (loginState.cli_port) {
    dest.searchParams.set("cli_port", String(loginState.cli_port));
  }
  return Response.redirect(dest.toString(), 302);
}

async function handleRedeem(request: Request, env: Env): Promise<Response> {
  let body: { code?: string; secret?: string; mode?: string };
  try {
    body = (await request.json()) as { code?: string; secret?: string; mode?: string };
  } catch {
    return bad("Invalid JSON body");
  }

  if (!body.code) {
    return bad("Missing code");
  }

  const raw = await env.AUTH_KV.get(`redeem:${body.code}`);
  if (!raw) {
    return bad("Unknown or expired code", 400);
  }
  const payload = JSON.parse(raw) as RedeemPayload;

  // Only trust mode stamped on the KV redeem payload (not the request body).
  const isCli = payload.mode === "cli";

  if (env.REDEEM_HMAC_SECRET && !isCli) {
    if (!body.secret || body.secret !== env.REDEEM_HMAC_SECRET) {
      return bad("Unauthorized redeem", 401);
    }
  }

  await env.AUTH_KV.delete(`redeem:${body.code}`);
  return json({
    access_token: payload.access_token,
    token_type: payload.token_type,
    scope: payload.scope,
    github_user: payload.github_user,
    installation_id: payload.installation_id ?? null,
  });
}
