# Native Otter API + Web (no Docker)
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File scripts/dev-native.ps1
# Optional: set $env:PGPASSWORD first if postgres user needs a password.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$Web = Join-Path $Root "apps\web"
$VenvPython = Join-Path $Api ".venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $Api ".venv\Scripts\uvicorn.exe"
$DataDir = Join-Path $Root "data\repositories"

Write-Host "== Otter native dev ==" -ForegroundColor Cyan

# Ensure Ollama is reachable
try {
  $null = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3
  Write-Host "Ollama: ok"
} catch {
  Write-Host "Ollama not responding on :11434 — start the Ollama app, then retry." -ForegroundColor Yellow
}

# Env for child processes (host-local, not Docker hostnames)
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:LLM_MODEL = if ($env:LLM_MODEL) { $env:LLM_MODEL } else { "qwen2.5-coder:7b" }
$env:LLM_API_KEY = ""
$env:LLM_FREE_FAILOVER = "true"
$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "postgresql+asyncpg://otter:otter@127.0.0.1:5432/otter" }
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6379/0" }
$env:REPOSITORY_DATA_DIR = $DataDir
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
$env:NEXT_PUBLIC_URL = "http://localhost:3000"
$env:PYTHONPATH = "$Api;$Root"

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating API venv..."
  Push-Location $Api
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  Pop-Location
}

# Ensure otter role/db exist (uses PGPASSWORD or prompts)
Write-Host "Ensuring Postgres role/database otter..."
& $VenvPython -c @"
import asyncio, asyncpg, os, getpass

async def main():
    admin_user = os.environ.get('PGUSER', 'postgres')
    admin_pass = os.environ.get('PGPASSWORD')
    if admin_pass is None:
        admin_pass = getpass.getpass(f'Postgres password for {admin_user}: ')
    conn = await asyncpg.connect(user=admin_user, password=admin_pass, database='postgres', host='127.0.0.1', port=5432)
    if not await conn.fetchval(\"select 1 from pg_roles where rolname='otter'\"):
        await conn.execute(\"create role otter login password 'otter'\")
        print('created role otter')
    else:
        await conn.execute(\"alter role otter with login password 'otter'\")
        print('role otter ready')
    if not await conn.fetchval(\"select 1 from pg_database where datname='otter'\"):
        await conn.execute('create database otter owner otter')
        print('created database otter')
    else:
        print('database otter ready')
    await conn.close()
    c = await asyncpg.connect(user='otter', password='otter', database='otter', host='127.0.0.1', port=5432)
    print('otter login ok')
    await c.close()

asyncio.run(main())
"@

Write-Host "Running migrations..."
Push-Location $Api
& $VenvPython -m alembic upgrade head
Pop-Location

if (-not (Test-Path (Join-Path $Web "node_modules"))) {
  Write-Host "Installing web deps..."
  Push-Location $Web
  npm install
  Pop-Location
}

Write-Host "Starting API on :8000 and Web on :3000 ..." -ForegroundColor Green
Start-Process -FilePath $VenvUvicorn -ArgumentList @("app.main:app","--reload","--host","127.0.0.1","--port","8000") -WorkingDirectory $Api
Start-Process -FilePath "npm" -ArgumentList @("run","dev","--","--port","3000") -WorkingDirectory $Web

Write-Host ""
Write-Host "Open http://localhost:3000"
Write-Host "API health: http://localhost:8000/health"
Write-Host "Note: repo import needs Redis+Celery; coding generate works without Redis if the repo is already local."
