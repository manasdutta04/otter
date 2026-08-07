# Otter platform — single custom image (API + web + worker).
# Official postgres/redis stay as separate Compose services.

# ---------------------------------------------------------------------------
# Web build
# ---------------------------------------------------------------------------
FROM node:20-bookworm-slim AS web-builder
WORKDIR /web

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY apps/web/ ./

ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ARG NEXT_PUBLIC_URL=http://127.0.0.1:3000
ARG NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3001
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_URL=${NEXT_PUBLIC_URL}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---------------------------------------------------------------------------
# Runtime — Python + Node copied from official Node image (no NodeSource apt)
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api \
    REPOSITORY_DATA_DIR=/data/repositories \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1 \
    PATH="/usr/local/node/bin:${PATH}"

# OS security updates + minimal packages (git for clone, supervisor/tini for process mgmt)
RUN apt-get update \
  && apt-get upgrade -y --no-install-recommends \
  && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
       supervisor \
       tini \
  && rm -rf /var/lib/apt/lists/*

# Copy Node binary only (standalone Next does not need npm at runtime)
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/node/bin/node
RUN node -v

WORKDIR /app

COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm /tmp/requirements.txt

COPY packages /app/packages
COPY apps/api /app/api

# Next.js standalone server + static assets
COPY --from=web-builder /web/.next/standalone /app/web
COPY --from=web-builder /web/.next/static /app/web/.next/static
COPY --from=web-builder /web/public /app/web/public

# Fix line endings and permissions for entrypoint when built on Windows hosts
COPY docker/platform/supervisord.conf /app/supervisord.conf
COPY docker/platform/entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh \
  && chmod +x /app/entrypoint.sh \
  && mkdir -p /data/repositories /var/log/supervisor \
  && useradd --create-home --uid 10001 --shell /usr/sbin/nologin otter \
  && chown -R otter:otter /app /data /var/log/supervisor

USER otter
EXPOSE 3000 8000
VOLUME ["/data/repositories"]

ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
