/** Local self-host product UI (Docker). Override in Vercel env. */
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");

export const APP_WORKSPACE = `${APP_URL}/app`;
export const APP_MODELS = `${APP_URL}/app/models`;

export const GITHUB_REPO = "https://github.com/manasdutta04/otter";
/** Canonical production marketing site (compose file + docs). */
export const PUBLIC_SITE = "https://otter.manasdutta.com";
export const DOCKER_HUB = "https://hub.docker.com/r/manasdutta04/otter";
export const DOCKER_IMAGE = "manasdutta04/otter:latest";
export const DOCKER_PULL = "docker pull manasdutta04/otter";

export const NPM_PACKAGE = "@otter-engg/cli";
/** Global install — puts `otter` on PATH (what the landing tabs should show). */
export const CLI_INSTALL_NPM = "npm i -g @otter-engg/cli";
export const CLI_INSTALL_NPM_GLOBAL = CLI_INSTALL_NPM;
export const CLI_INSTALL_PNPM = "pnpm add -g @otter-engg/cli";
export const CLI_INSTALL_YARN = "yarn global add @otter-engg/cli";
export const CLI_INSTALL_BUN = "bun add -g @otter-engg/cli";

export const PYPI_PACKAGE = "otter-mcp";
export const PYPI_URL = "https://pypi.org/project/otter-mcp/";
export const MCP_INSTALL_PIP = "pip install otter-mcp";
export const MCP_INSTALL_UVX = "uvx otter-mcp";

/**
 * Marketing site origin (hosts /docker-compose.yml so users never need to clone).
 * Prefer NEXT_PUBLIC_SITE_URL in production; fall back to the public domain, then local.
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : PUBLIC_SITE)
).replace(/\/$/, "");

/** Compose quickstart (full stack with Postgres + Redis). */
export const DOCKER_QUICKSTART = `docker compose -f ${SITE_URL}/docker-compose.yml up -d`;
export const DOCKER_COMPOSE_UP = DOCKER_QUICKSTART;
