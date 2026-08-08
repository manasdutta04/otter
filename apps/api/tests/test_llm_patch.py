"""Unit tests for patch generation helpers."""
from __future__ import annotations

import json

import pytest

from app.llm import (
    PatchGenerationError,
    deterministic_patch,
    is_health_request,
    is_todo_only_patch,
)


def test_is_health_request():
    assert is_health_request("Add a /health endpoint")
    assert not is_health_request("Add email password authentication")


def test_deterministic_patch_rejects_feature_todos():
    files = [{"path": "server/routes.ts", "content": "export function registerRoutes() {}\n"}]
    with pytest.raises(PatchGenerationError):
        deterministic_patch("Add email password authentication for login", files)


def test_deterministic_health_patch_for_express_like_file():
    files = [
        {
            "path": "server/index.ts",
            "content": "import express from 'express';\nconst app = express();\n",
        }
    ]
    patch = deterministic_patch("Add a /health API endpoint", files)
    assert patch["source"] == "deterministic"
    assert "/health" in str(patch["files"][0]["content"])
    assert "TODO(Otter)" not in str(patch["files"][0]["content"])


def test_is_todo_only_patch_detects_marker_addition():
    original = "export function registerRoutes() {\n  return true;\n}\n"
    patched = (
        original.rstrip()
        + "\n\n// TODO(Otter): add auth\n// Implement carefully and remove this marker when done.\n\n"
    )
    assert is_todo_only_patch(
        [{"path": "server/routes.ts", "content": patched}],
        {"server/routes.ts": original},
    )


def test_is_todo_only_patch_allows_real_change():
    original = "export function registerRoutes() {\n  return true;\n}\n"
    patched = "export function registerRoutes() {\n  app.post('/login', handler);\n  return true;\n}\n"
    assert not is_todo_only_patch(
        [{"path": "server/routes.ts", "content": patched}],
        {"server/routes.ts": original},
    )


def test_free_model_candidates_prefer_primary_then_failover():
    from app.llm import _free_model_candidates

    models = _free_model_candidates("qwen2.5-coder:7b", free_failover=True)
    assert models[0] == "qwen2.5-coder:7b"
    assert "gemma4:e2b" in models
    assert models.count("qwen2.5-coder:7b") == 1


def test_ollama_allows_empty_api_key(monkeypatch):
    from app.config import Settings, get_settings
    from app.llm import _is_ollama_base, _supports_json_object, _validate_llm_settings

    get_settings.cache_clear()
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-coder:7b")
    monkeypatch.setenv("LLM_BASE_URL", "http://host.docker.internal:11434/v1")
    # Bypass cached Settings from process env files
    monkeypatch.setattr(
        "app.llm.get_settings",
        lambda: Settings(
            llm_api_key="",
            llm_model="qwen2.5-coder:7b",
            llm_base_url="http://host.docker.internal:11434/v1",
        ),
    )
    key, model, base = _validate_llm_settings()
    assert key == "ollama"
    assert model == "qwen2.5-coder:7b"
    assert _is_ollama_base(base)
    assert _supports_json_object(base) is False


def test_non_ollama_requires_api_key(monkeypatch):
    from app.llm import PatchGenerationError, _validate_llm_settings
    from app.llm_settings import LlmRuntime

    monkeypatch.setattr(
        "app.llm_settings.get_effective_runtime_sync",
        lambda: LlmRuntime(
            provider="openai_compatible",
            api_key="",
            model="some-model",
            base_url="https://api.example.com/v1",
            free_failover=False,
        ),
    )
    with pytest.raises(PatchGenerationError, match="API key|api key|LLM API key"):
        _validate_llm_settings()


def test_resolve_base_url_prefers_ipv4_for_docker_host(monkeypatch):
    from app.llm import _resolve_base_url
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.65.254", 11434))],
    )
    resolved = _resolve_base_url("http://host.docker.internal:11434/v1")
    assert resolved == "http://192.168.65.254:11434/v1"


def test_salvage_recovers_complete_files_from_truncated_json():
    from app.llm import _extract_json_object

    truncated = (
        '{"summary":"Added auth","files":['
        '{"path":"server/auth.ts","content":"import bcrypt from \'bcrypt\';\\n"},'
        '{"path":"package.json","content":"{\\n  \\"name\\": \\"greetings-ca'
    )
    data = _extract_json_object(truncated)
    assert data["summary"] == "Added auth"
    assert [item["path"] for item in data["files"]] == ["server/auth.ts"]
    assert data["truncated"] is True


def test_dependency_delta_merges_into_package_json():
    from app.llm import _normalize_patch

    originals = {
        "package.json": json.dumps({"name": "app", "dependencies": {"express": "^4.21.2"}}),
        "server/auth.ts": "export {};\n",
    }
    result = {
        "summary": "Add login",
        "dependencies": {"bcrypt": "^5.1.1"},
        "files": [
            {
                "path": "shared/schema.ts",
                "content": (
                    'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
                    'export const users = pgTable("users", {\n'
                    '  id: uuid("id").primaryKey(),\n'
                    '  email: text("email").notNull(),\n'
                    '  passwordHash: text("password_hash").notNull(),\n'
                    "});\n"
                ),
            },
            {
                "path": "server/auth.ts",
                "content": (
                    "import bcrypt from 'bcrypt';\n"
                    "app.post('/api/login', async () => {\n"
                    "  const passwordHash = await bcrypt.hash(pw, 10);\n"
                    "});\n"
                ),
            },
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add login authentication")
    manifest = next(item for item in patch["files"] if item["path"] == "package.json")
    assert json.loads(manifest["content"])["dependencies"]["bcrypt"] == "^5.1.1"


def test_auto_adds_imported_bcryptjs_when_dependencies_omitted():
    from app.llm import _normalize_patch

    originals = {
        "package.json": json.dumps({"name": "app", "dependencies": {"express": "^4.21.2", "passport": "^0.7.0"}}),
    }
    result = {
        "summary": "Add login",
        "files": [
            {
                "path": "shared/schema.ts",
                "content": (
                    'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
                    'export const users = pgTable("users", {\n'
                    '  id: uuid("id").primaryKey(),\n'
                    '  email: text("email").notNull(),\n'
                    '  passwordHash: text("password_hash").notNull(),\n'
                    "});\n"
                ),
            },
            {
                "path": "server/routes.ts",
                "content": (
                    "import bcryptjs from 'bcryptjs';\n"
                    "app.post('/api/register', async (req, res) => {\n"
                    "  const passwordHash = await bcryptjs.hash(req.body.password, 10);\n"
                    "  res.json({ ok: true });\n"
                    "});\n"
                    "app.post('/api/login', async () => {});\n"
                ),
            },
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add email password authentication")
    manifest = next(item for item in patch["files"] if item["path"] == "package.json")
    deps = json.loads(manifest["content"])["dependencies"]
    assert deps["bcryptjs"] == "^2.4.3"
    assert deps["express"] == "^4.21.2"


def test_auto_adds_bcryptjs_even_when_package_json_context_is_truncated():
    from app.llm import _normalize_patch

    # Force invalid JSON like the old 3k context truncate did.
    truncated = '{\n  "name": "greetings-card",\n  "dependencies": {\n    "express": "^4.21.2",\n    "passport": "^0.7'
    with pytest.raises(json.JSONDecodeError):
        json.loads(truncated)
    originals = {"package.json": truncated}
    result = {
        "summary": "Add login",
        "files": [
            {
                "path": "shared/schema.ts",
                "content": (
                    'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
                    'export const users = pgTable("users", {\n'
                    '  id: uuid("id").primaryKey(),\n'
                    '  email: text("email").notNull(),\n'
                    '  passwordHash: text("password_hash").notNull(),\n'
                    "});\n"
                ),
            },
            {
                "path": "server/routes.ts",
                "content": (
                    "import bcryptjs from 'bcryptjs';\n"
                    "app.post('/api/register', async (req) => {\n"
                    "  const passwordHash = await bcryptjs.hash(req.body.password, 10);\n"
                    "});\n"
                    "app.post('/api/login', async () => {});\n"
                ),
            },
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add email password authentication")
    manifest = next(item for item in patch["files"] if item["path"] == "package.json")
    assert "bcryptjs" in json.loads(manifest["content"])["dependencies"]


def test_model_rewritten_package_json_is_reduced_to_a_delta():
    from app.llm import _normalize_patch

    originals = {
        "package.json": json.dumps(
            {"name": "app", "dependencies": {"express": "^4.21.2", "drizzle-orm": "0.39.3"}}
        ),
    }
    result = {
        "summary": "Add login",
        "files": [
            {
                "path": "package.json",
                "content": json.dumps({"name": "renamed", "dependencies": {"bcrypt": "^5.1.1"}}),
            },
            {
                "path": "shared/schema.ts",
                "content": (
                    'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
                    'export const users = pgTable("users", {\n'
                    '  id: uuid("id").primaryKey(),\n'
                    '  email: text("email").notNull(),\n'
                    '  passwordHash: text("password_hash").notNull(),\n'
                    "});\n"
                ),
            },
            {
                "path": "server/auth.ts",
                "content": (
                    "import bcrypt from 'bcrypt';\n"
                    "app.post('/api/register', async () => {\n"
                    "  const passwordHash = await bcrypt.hash(pw, 10);\n"
                    "});\n"
                ),
            },
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add login authentication")
    manifest = next(item for item in patch["files"] if item["path"] == "package.json")
    data = json.loads(manifest["content"])
    assert data["name"] == "app"
    assert data["dependencies"] == {
        "bcrypt": "^5.1.1",
        "drizzle-orm": "0.39.3",
        "express": "^4.21.2",
    }

def test_validate_rejects_hallucinated_auth_patch():
    from app.llm import validate_patch_quality

    originals = {
        "package.json": json.dumps(
            {
                "dependencies": {
                    "drizzle-orm": "0.39.3",
                    "express": "4.21.2",
                    "pg": "8.16.3",
                }
            }
        ),
        "shared/schema.ts": (
            'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
            'export const cards = pgTable("cards", { id: uuid("id").primaryKey() });\n'
        ),
        "server/db.ts": (
            'import { drizzle } from "drizzle-orm/node-postgres";\n'
            "import pg from \"pg\";\n"
            "export const db = drizzle(new pg.Pool({ connectionString: process.env.DATABASE_URL }));\n"
        ),
    }
    files = [
        {
            "path": "shared/schema.ts",
            "content": "import { z } from 'zod';\nexport const cards = z.object({ id: z.string() });\n",
        },
        {
            "path": "server/db.ts",
            "content": (
                "import { drizzle } from 'drizzle-orm';\n"
                "import { pgDriver } from '@drizzle/driver-pg';\n"
                "export const db = drizzle(pgDriver).database('mydb');\n"
            ),
        },
        {
            "path": "server/routes.ts",
            "content": (
                "const hashedPassword = password;\n"
                "await db.insert('users').values({ email, password: hashedPassword });\n"
                "if (user.password !== password) return;\n"
                "app.post('/api/login', () => {});\n"
            ),
        },
    ]
    with pytest.raises(ValueError, match="low-quality"):
        validate_patch_quality("add email/password authentication", files, originals)


def test_validate_allows_hashed_auth_with_drizzle():
    from app.llm import validate_patch_quality

    originals = {
        "package.json": json.dumps(
            {
                "dependencies": {
                    "bcrypt": "5.1.1",
                    "drizzle-orm": "0.39.3",
                    "express": "4.21.2",
                    "pg": "8.16.3",
                }
            }
        ),
        "shared/schema.ts": (
            'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
            'export const cards = pgTable("cards", { id: uuid("id").primaryKey() });\n'
        ),
    }
    files = [
        {
            "path": "shared/schema.ts",
            "content": (
                'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
                'export const cards = pgTable("cards", { id: uuid("id").primaryKey() });\n'
                'export const users = pgTable("users", {\n'
                '  id: uuid("id").primaryKey(),\n'
                '  email: text("email").notNull(),\n'
                '  passwordHash: text("password_hash").notNull(),\n'
                "});\n"
            ),
        },
        {
            "path": "server/routes.ts",
            "content": (
                "import bcrypt from 'bcrypt';\n"
                "import { users } from '@shared/schema';\n"
                "app.post('/api/register', async (req, res) => {\n"
                "  const passwordHash = await bcrypt.hash(req.body.password, 10);\n"
                "  await db.insert(users).values({ email: req.body.email, passwordHash });\n"
                "  res.json({ ok: true });\n"
                "});\n"
                "app.post('/api/login', async () => {});\n"
            ),
        },
    ]
    validate_patch_quality("add email/password authentication", files, originals)


def test_validate_rejects_greetings_card_stub_auth():
    """PR #2 style: login against cards + stub session + drizzle .get()."""
    from app.llm import validate_patch_quality

    originals = {
        "package.json": json.dumps(
            {
                "dependencies": {
                    "bcryptjs": "2.4.3",
                    "drizzle-orm": "0.39.3",
                    "express": "4.21.2",
                    "pg": "8.16.3",
                }
            }
        ),
        "shared/schema.ts": (
            'import { pgTable, text, uuid } from "drizzle-orm/pg-core";\n'
            'export const cards = pgTable("cards", {\n'
            '  id: uuid("id").primaryKey(),\n'
            '  recipientName: text("recipient_name"),\n'
            "});\n"
        ),
    }
    files = [
        {
            "path": "server/routes.ts",
            "content": (
                "import { sql, eq } from 'drizzle-orm';\n"
                "import bcrypt from 'bcryptjs';\n"
                "import { cards } from '@shared/schema';\n"
                "app.post('/api/auth/login', async (req, res) => {\n"
                "  const { email, password } = req.body;\n"
                "  // Replace with actual user lookup logic\n"
                "  const user = await db.select().from(cards).where(eq(cards.recipientName, email)).get();\n"
                "  if (!user) return res.status(401).json({ message: 'Invalid credentials' });\n"
                "  const isPasswordValid = await bcrypt.compare(password, user.password);\n"
                "  // Replace with actual session management logic\n"
                "  req.session.userId = user.id;\n"
                "  res.json({ message: 'Logged in successfully' });\n"
                "});\n"
            ),
        },
    ]
    with pytest.raises(ValueError, match="low-quality"):
        validate_patch_quality(
            "I want to add one email/password authentication before opening the main",
            files,
            originals,
        )


def test_strip_llm_summary_prefix():
    from app.llm import strip_llm_summary_prefix

    assert strip_llm_summary_prefix("[llm:qwen2.5-coder:7b] Add login") == "Add login"
    assert strip_llm_summary_prefix("[llm:a] [llm:b] Nested") == "Nested"
    assert strip_llm_summary_prefix("Clean summary") == "Clean summary"


def test_normalize_patch_strips_model_prefix_from_summary():
    from app.llm import _normalize_patch

    originals = {"server/routes.ts": "export {};\n"}
    result = {
        "summary": "[llm:qwen2.5-coder:7b] Adds a health route",
        "files": [{"path": "server/routes.ts", "content": "export const ok = true;\n"}],
    }
    patch = _normalize_patch(result, originals=originals, request="add health")
    assert "[llm:" not in str(patch["summary"]).lower()
    assert "health" in str(patch["summary"]).lower()

