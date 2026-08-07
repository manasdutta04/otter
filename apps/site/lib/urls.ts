/** Local self-host product UI (Docker). Override in Vercel env. */
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");

export const APP_WORKSPACE = `${APP_URL}/app`;
export const APP_MODELS = `${APP_URL}/app/models`;

export const GITHUB_REPO = "https://github.com/manasdutta04/otter";
export const DOCKER_HUB = "https://hub.docker.com/r/manasdutta04/otter";
export const DOCKER_IMAGE = "manasdutta04/otter:latest";

/**
 * Marketing site origin (hosts /docker-compose.yml so users never need to clone).
 * Prefer NEXT_PUBLIC_SITE_URL in production (your Vercel domain).
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://127.0.0.1:3001")
).replace(/\/$/, "");

/** One-line no-clone install (compose file is public on the marketing site). */
export const DOCKER_QUICKSTART = `docker compose -f ${SITE_URL}/docker-compose.yml up -d`;
