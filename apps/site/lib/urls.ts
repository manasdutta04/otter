/** Local self-host product UI (Docker). Override in Vercel env. */
export const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3000").replace(/\/$/, "");

export const APP_WORKSPACE = `${APP_URL}/app`;
export const APP_MODELS = `${APP_URL}/app/models`;

export const GITHUB_REPO = "https://github.com/manasdutta04/otter";
export const DOCKER_HUB = "https://hub.docker.com/r/manasdutta04/otter";
export const DOCKER_IMAGE = "manasdutta04/otter:latest";

/** Copy-paste self-host quickstart for the landing + docs. */
export const DOCKER_QUICKSTART = `git clone https://github.com/manasdutta04/otter.git
cd otter
docker compose -f docker/compose.platform.yml pull
docker compose -f docker/compose.platform.yml up -d`;
