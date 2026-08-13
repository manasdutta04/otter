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


def test_auth_request_ignores_register_route_and_basic_copy():
    from app.llm import _is_auth_request

    assert not _is_auth_request("Register it with the existing Express app alongside user routes.")
    assert not _is_auth_request("Change auth_basic denial text to Authentication required")
    assert _is_auth_request("Add email password authentication for login")
    assert _is_auth_request("Add POST /users/login that verifies an email and password")


def test_extract_json_object_strips_markdown_and_preamble():
    from app.llm import _extract_json_object

    fenced = """Sure.\n```json\n{"summary":"ok","files":[{"path":"a.py","content":"x"}]}\n```\n"""
    data = _extract_json_object(fenced)
    assert data["summary"] == "ok"
    assert data["files"][0]["path"] == "a.py"

    preamble = 'Here you go:\n{"summary":"done","files":[{"path":"b.py","content":"y"}]}'
    data = _extract_json_object(preamble)
    assert data["summary"] == "done"


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
        "package.json": json.dumps(
            {"name": "app", "dependencies": {"express": "^4.21.2", "drizzle-orm": "0.39.3"}}
        ),
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


def test_inferred_imports_do_not_auto_append_package_json():
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
    with pytest.raises(ValueError, match="QUALITY_GATE|not in package.json|low-quality|unexpected_dependency"):
        _normalize_patch(result, originals=originals, request="add email password authentication")


def test_truncated_full_file_json_is_rejected():
    from app.llm import _normalize_patch

    originals = {"server/auth.ts": "export {};\n"}
    result = {
        "summary": "Added auth",
        "files": [{"path": "server/auth.ts", "content": "import bcrypt from 'bcrypt';\n"}],
        "truncated": True,
    }
    with pytest.raises(ValueError, match="Truncated"):
        _normalize_patch(result, originals=originals, request="add login")


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
    with pytest.raises(ValueError, match="QUALITY_GATE|low-quality|invented"):
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
    with pytest.raises(ValueError, match="QUALITY_GATE|low-quality|invented|auth"):
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


def test_normalize_patch_does_not_invent_package_json_for_python_only():
    from app.llm import _normalize_patch

    originals = {"bottle.py": "def tob(x): return x\n"}
    result = {
        "summary": "Add email helper",
        "dependencies": {"bcrypt": "^3.2.0"},
        "files": [{"path": "bottle.py", "content": "def tob(x): return x\n\ndef is_valid_email(value): return '@' in value\n"}],
    }
    patch = _normalize_patch(result, originals=originals, request="add is_valid_email")
    assert all(item["path"] != "package.json" for item in patch["files"])
    assert any(item["path"] == "bottle.py" for item in patch["files"])


def test_edits_normalize_for_existing_file():
    from app.llm import _normalize_patch

    originals = {"utils.py": "def add(a, b):\n    return a + b\n"}
    result = {
        "summary": "Add multiply",
        "edits": [
            {
                "path": "utils.py",
                "old_string": "def add(a, b):\n    return a + b\n",
                "new_string": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n",
            }
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add multiply helper")
    assert patch["files"][0]["path"] == "utils.py"
    assert "def multiply" in patch["files"][0]["content"]
    assert "def add" in patch["files"][0]["content"]


def test_stub_rewrite_of_existing_library_is_rejected():
    from app.llm import _normalize_patch

    originals = {
        "bottle.py": (
            "class Bottle:\n    def run(self):\n        return True\n\n"
            "def auth_basic(func):\n    return func\n\n"
            "def tob(value):\n    return value\n"
        )
        * 20
    }
    result = {
        "summary": "Add TimingPlugin",
        "files": [{"path": "bottle.py", "content": "class TimingPlugin:\n    pass\n"}],
    }
    with pytest.raises(ValueError, match="Destructive rewrite|shorter|dropped"):
        _normalize_patch(result, originals=originals, request="add TimingPlugin")


def test_retry_prompt_contains_validation_error():
    from app.llm import _is_retryable_validation_error, _json_repair_user_message, _retry_user_message

    message = _retry_user_message("Python syntax error in bottle.py")
    assert "Python syntax error in bottle.py" in message
    assert "edits" in message.lower()
    assert _is_retryable_validation_error(ValueError("Invalid patch shape: missing files/edits"))
    assert not _is_retryable_validation_error("qwen2.5-coder:7b timed out after 300s")
    compact = _json_repair_user_message("No JSON object found", '{"summary":')
    assert "STRUCTURAL JSON ERROR" in compact
    assert "FILE:" not in compact
    assert "bottle.py" not in compact
    assert "Previous response to repair" in compact


def test_empty_old_string_appends_to_existing_python_file():
    from app.llm import _normalize_patch

    originals = {"utils.py": "def add(a, b):\n    return a + b\n"}
    result = {
        "summary": "Add multiply",
        "edits": [{"path": "utils.py", "old_string": "", "new_string": "\ndef multiply(a, b):\n    return a * b\n"}],
    }
    patch = _normalize_patch(result, originals=originals, request="add multiply helper")
    body = patch["files"][0]["content"]
    assert "def add" in body
    assert "def multiply" in body


def test_nested_file_edits_and_new_ts_file():
    from app.llm import _normalize_patch

    originals = {"src/app.ts": "export const n = 1;\n"}
    result = {
        "summary": "Add helper and new util",
        "files": [
            {
                "path": "src/app.ts",
                "edits": [{"old": "export const n = 1;", "new": "export const n = 2;"}],
            },
            {"path": "src/util.ts", "content": "export const k = 3;\n"},
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add util helper")
    by_path = {item["path"]: item["content"] for item in patch["files"]}
    assert by_path["src/app.ts"] == "export const n = 2;\n"
    assert by_path["src/util.ts"] == "export const k = 3;\n"


def test_excerpt_disambiguates_non_unique_old_string():
    from packages.agent.patch import apply_edits_to_originals

    full = "def one():\n    return 1\n\ndef two():\n    return 1\n"
    excerpt = "def two():\n    return 1\n"
    files = apply_edits_to_originals(
        [{"path": "m.py", "old_string": "    return 1\n", "new_string": "    return 2\n"}],
        {"m.py": full},
        excerpts={"m.py": excerpt},
    )
    assert files[0]["content"].count("return 2") == 1
    assert "def one():\n    return 1" in files[0]["content"]


def test_quality_gate_error_is_structured():
    from packages.agent.patch import QualityGateError, materialize_safe_patch

    with pytest.raises(QualityGateError, match="category: edit_target_not_found") as caught:
        materialize_safe_patch(
            {"summary": "x", "edits": [{"path": "a.py", "old_string": "missing", "new_string": "x"}]},
            {"a.py": "def ok():\n    return 1\n"},
        )
    assert caught.value.category == "edit_target_not_found"
    assert caught.value.file == "a.py"


def test_extract_repairs_triple_quoted_json_and_fences():
    from app.llm import _extract_json_object

    raw = (
        '```json\n{"summary":"ok","edits":[{"path":"a.py","old_string":"",'
        '"new_string": """\ndef add(a, b):\n    return a + b\n""" }]}\n```'
    )
    data = _extract_json_object(raw)
    assert data["summary"] == "ok"
    assert "def add" in data["edits"][0]["new_string"]
    assert data.get("_local_repair") is True


def test_salvage_keeps_complete_edits_from_truncated_files_array():
    from app.llm import _extract_json_object, _normalize_patch

    truncated = (
        '{"summary":"Added helper","edits":['
        '{"path":"bottle.py","old_string":"","new_string":"\\ndef is_valid_email(v):\\n    return True\\n"}'
        '],"files":[{"path":"test/test_html_helper.py","content":"import unittest\\nclass T'
    )
    data = _extract_json_object(truncated)
    assert data["edits"][0]["path"] == "bottle.py"
    originals = {"bottle.py": "def tob(x):\n    return x\n"}
    patch = _normalize_patch(data, originals=originals, request="add is_valid_email")
    assert "def is_valid_email" in patch["files"][0]["content"]
    assert "def tob" in patch["files"][0]["content"]
    assert patch.get("_local_repair") is True


def test_valid_json_without_repair_is_raw_structured():
    from app.llm import _extract_json_object

    data = _extract_json_object('{"summary":"ok","files":[{"path":"a.py","content":"x"}]}')
    assert data["summary"] == "ok"
    assert "_local_repair" not in data


def test_keep_good_edit_when_files_array_is_destructive():
    from app.llm import _normalize_patch

    original = "def get_bool(v):\n    return bool(v)\n" + ("x = 1\n" * 80)
    result = {
        "summary": "Add get_bool helper and stub tests",
        "edits": [{"path": "starlette/config.py", "old_string": "", "new_string": "\ndef extra():\n    return 1\n"}],
        "files": [{"path": "tests/test_config.py", "content": "def test_stub():\n    assert True\n"}],
    }
    originals = {
        "starlette/config.py": "def existing():\n    return 0\n",
        "tests/test_config.py": original,
    }
    patch = _normalize_patch(result, originals=originals, request="add get_bool")
    by_path = {item["path"]: item["content"] for item in patch["files"]}
    assert "def extra" in by_path["starlette/config.py"]
    assert "def existing" in by_path["starlette/config.py"]
    assert "tests/test_config.py" not in by_path


def test_destructive_rewrite_still_rejected_when_it_is_the_only_change():
    from app.llm import _normalize_patch

    original = "class MyPlugin:\n    pass\n\nclass Other:\n    pass\n" + ("x = 1\n" * 80)
    result = {
        "summary": "stub",
        "files": [{"path": "test/test_plugins.py", "content": "class TimingPlugin:\n    pass\n"}],
    }
    with pytest.raises(ValueError, match="Destructive rewrite|shorter|dropped"):
        _normalize_patch(result, originals={"test/test_plugins.py": original}, request="add plugin")


def test_symbol_scoped_edit_and_quote_mismatch():
    from packages.agent.patch import apply_edits_to_originals

    source = (
        'def auth_basic(check, realm="private", text="Access denied"):\n'
        "    return text\n\n"
        'def other():\n    return "Access denied."\n'
    )
    files = apply_edits_to_originals(
        [
            {
                "path": "bottle.py",
                "symbol": "auth_basic",
                "old_string": "return 'Access denied'",
                "new_string": "return 'Authentication required'",
            }
        ],
        {"bottle.py": source},
    )
    body = files[0]["content"]
    assert 'text="Authentication required"' in body
    assert 'return "Access denied."' in body


def test_quote_style_swap_is_unique_not_fuzzy():
    from packages.agent.patch import apply_edits_to_originals

    source = 'app.post("/users", async (req, res) => {\n  res.json({});\n});\n'
    files = apply_edits_to_originals(
        [
            {
                "path": "src/routes/users.ts",
                "old_string": "app.post('/users', async (req, res) => {",
                "new_string": "app.post('/users', async (req, res) => {\n  // keep",
            }
        ],
        {"src/routes/users.ts": source},
    )
    assert "// keep" in files[0]["content"]
    assert 'app.post("/users"' in files[0]["content"] or "app.post('/users'" in files[0]["content"]


def test_missing_symbol_falls_back_to_unique_old_string():
    from packages.agent.patch import apply_edits_to_originals

    source = "export async function createUser(email: string) {\n  return email;\n}\n"
    files = apply_edits_to_originals(
        [
            {
                "path": "src/services/userService.ts",
                "symbol": "validateEmail",
                "old_string": "return email;",
                "new_string": "return email.trim();",
            }
        ],
        {"src/services/userService.ts": source},
    )
    assert "email.trim()" in files[0]["content"]
    assert "createUser" in files[0]["content"]


def test_ambiguous_symbol_is_rejected():
    from packages.agent.patch import QualityGateError, apply_edits_to_originals

    source = "def helper():\n    return 1\n\ndef helper():\n    return 2\n"
    with pytest.raises(QualityGateError, match="ambiguous_anchor") as caught:
        apply_edits_to_originals(
            [{"path": "a.py", "symbol": "helper", "old_string": "return 1", "new_string": "return 3"}],
            {"a.py": source},
        )
    assert caught.value.category == "ambiguous_anchor"


def test_changes_contract_maps_to_edits():
    from app.llm import _normalize_patch

    originals = {"utils.py": "def add(a, b):\n    return a + b\n"}
    result = {
        "summary": "Add multiply",
        "changes": [
            {
                "file": "utils.py",
                "operation": "append",
                "content": "\ndef multiply(a, b):\n    return a * b\n",
            }
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="add multiply")
    assert "def multiply" in patch["files"][0]["content"]
    assert "def add" in patch["files"][0]["content"]


def test_new_python_file_syntax_error_is_rejected():
    from packages.agent.patch import QualityGateError, materialize_safe_patch

    with pytest.raises(QualityGateError, match="syntax_error|never closed") as caught:
        materialize_safe_patch(
            {
                "summary": "add middleware test",
                "files": [
                    {
                        "path": "tests/middleware/test_request_id.py",
                        "content": "def test_ok():\n    assert send(\n",
                    }
                ],
            },
            {},
        )
    assert caught.value.category == "syntax_error"


def test_auth_patch_on_existing_user_repository_is_allowed():
    from app.llm import validate_patch_quality

    originals = {
        "src/repositories/userRepository.ts": "export async function insertUser(email: string) {\n  return { id: '1', email };\n}\n",
        "src/services/userService.ts": "export async function createUser(email: string) {\n  return insertUser(email);\n}\n",
        "src/routes/users.ts": "app.post('/users', async () => {});\n",
    }
    files = [
        {
            "path": "src/repositories/userRepository.ts",
            "content": (
                "export async function insertUser(email: string, passwordHash: string) {\n"
                "  return { id: '1', email, passwordHash };\n"
                "}\n"
            ),
        },
        {
            "path": "src/services/userService.ts",
            "content": (
                "import { scrypt } from 'node:crypto';\n"
                "export async function createUser(email: string, password: string) {\n"
                "  const passwordHash = await crypto.scrypt(password, 'salt', 32);\n"
                "  return insertUser(email, passwordHash);\n"
                "}\n"
                "export async function loginUser(email: string, password: string) {\n"
                "  return true;\n"
                "}\n"
            ),
        },
        {
            "path": "src/routes/users.ts",
            "content": (
                "app.post('/users/login', async (req, res) => {\n"
                "  res.status(401).json({ error: 'unauthorized' });\n"
                "});\n"
            ),
        },
    ]
    validate_patch_quality(
        "Add POST /users/login that verifies an email and password",
        files,
        originals,
    )


def test_auth_still_rejects_undeclared_npm_import():
    from app.llm import validate_patch_quality

    originals = {
        "src/repositories/userRepository.ts": "export async function insertUser(email: string) { return { email }; }\n",
        "src/services/userService.ts": "export async function createUser(email: string) { return insertUser(email); }\n",
    }
    files = [
        {
            "path": "src/services/userService.ts",
            "content": (
                "import bcrypt from 'bcrypt';\n"
                "export async function createUser(email, password) {\n"
                "  const passwordHash = await bcrypt.hash(password, 10);\n"
                "  return insertUser(email, passwordHash);\n"
                "}\n"
            ),
        },
        {
            "path": "src/routes/users.ts",
            "content": "app.post('/users/login', async () => {});\n",
        },
    ]
    with pytest.raises(ValueError, match="QUALITY_GATE|not in package.json|incomplete_auth|unexpected_dependency"):
        validate_patch_quality("Add POST /users/login email password authentication", files, originals)


def test_legitimate_multi_file_edit_and_declared_dependency():
    from app.llm import _normalize_patch

    originals = {
        "package.json": '{"name":"app","dependencies":{"express":"^4.21.2"}}',
        "src/routes/users.ts": 'app.post("/users", async () => {});\n',
        "src/services/userService.ts": "export async function createUser(email: string) { return email; }\n",
    }
    result = {
        "summary": "Add login and hash helper",
        "dependencies": {"bcrypt": "^5.1.1"},
        "edits": [
            {
                "path": "src/routes/users.ts",
                "old_string": 'app.post("/users", async () => {});',
                "new_string": (
                    'app.post("/users", async () => {});\n'
                    'app.post("/users/login", async () => {});'
                ),
            },
            {
                "path": "src/services/userService.ts",
                "old_string": "",
                "new_string": (
                    "\nimport bcrypt from 'bcrypt';\n"
                    "export async function loginUser(email: string, password: string) {\n"
                    "  const passwordHash = await bcrypt.hash(password, 10);\n"
                    "  return passwordHash;\n"
                    "}\n"
                ),
            },
        ],
    }
    patch = _normalize_patch(
        result,
        originals=originals,
        request="Add POST /users/login email password authentication",
    )
    by_path = {item["path"]: item["content"] for item in patch["files"]}
    assert "/users/login" in by_path["src/routes/users.ts"]
    assert "bcrypt" in by_path["src/services/userService.ts"]
    assert "bcrypt" in json.loads(by_path["package.json"])["dependencies"]


def test_syntax_preserving_edit_keeps_existing_python():
    from app.llm import _normalize_patch

    originals = {"mod.py": "def one():\n    return 1\n\ndef two():\n    return 2\n"}
    result = {
        "summary": "rename return",
        "edits": [
            {
                "path": "mod.py",
                "symbol": "two",
                "old_string": "return 2",
                "new_string": "return 22",
            }
        ],
    }
    patch = _normalize_patch(result, originals=originals, request="change two")
    body = patch["files"][0]["content"]
    assert "def one():\n    return 1" in body
    assert "return 22" in body

