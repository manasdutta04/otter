#!/bin/sh
set -eu

wait_tcp() {
  host="$1"
  port="$2"
  name="$3"
  tries=60
  i=0
  echo "Waiting for ${name} at ${host}:${port}..."
  while [ "$i" -lt "$tries" ]; do
    if python -c "import socket; s=socket.create_connection(('${host}', int('${port}')), 1); s.close()" 2>/dev/null; then
      echo "${name} is ready."
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "Timed out waiting for ${name} (${host}:${port})" >&2
  exit 1
}

PG_HOST="${POSTGRES_HOST:-postgres}"
PG_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

wait_tcp "$PG_HOST" "$PG_PORT" "Postgres"
wait_tcp "$REDIS_HOST" "$REDIS_PORT" "Redis"

echo "Running database migrations..."
cd /app/api
alembic upgrade head

echo "Starting Otter platform (API + web + worker)..."
exec /usr/bin/supervisord -n -c /app/supervisord.conf
