"""LLM helpers for approval-gated coding tasks."""
from __future__ import annotations

import json
import logging
import re
import socket
import time
from pathlib import Path

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


def _edit_prompt_addon() -> str:
    try:
        from packages.agent.patch import edit_prompt_addon

        return f"{edit_prompt_addon()}\n"
    except Exception:  # noqa: BLE001 — keep generate usable without agent package
        return ""


HEALTH_PATTERNS = (
    re.compile(r"[\"']/health[\"']"),
    re.compile(r"@app\.get\(\s*[\"']/health"),
    re.compile(r"router\.(get|Get)\(\s*[\"']/health"),
    re.compile(r"export\s+async\s+function\s+GET"),
)

TODO_MARKER_RE = re.compile(r"TODO\(Otter\)", re.IGNORECASE)
PLACEHOLDER_MODELS = {
    "",
    "changeme",
    "your-model",
    "sk-your-key-here",
}

# Local Ollama coding models. Order = failover priority (coder → compact).
# Tags must match `ollama list` on the host.
FREE_CODING_MODELS: tuple[str, ...] = (
    "qwen2.5-coder:7b",
    "gemma4:e2b",
)

# Whole-file patches are token-hungry; keep a modest budget so 7B models finish JSON.
MAX_COMPLETION_TOKENS = 2048
# Prompt context caps for local 7B-class models (chars, not tokens).
# Keep generate input inside OLLAMA_NUM_CTX=4096; 6x3000 overflowed and caused refuse/stub JSON.
CONTEXT_FILE_LIMIT = 4
CONTEXT_CHARS_PER_FILE = 1800
# Keep Ollama KV cache small so 7B models fit in limited host RAM.
OLLAMA_NUM_CTX = 4096


# Manifests the model must never rewrite wholesale — it declares deps instead.
MANIFEST_PATHS = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "requirements.txt",
    "pyproject.toml",
}

AUTH_PATH_TERMS = (
    "auth",
    "login",
    "session",
    "passport",
    "next-auth",
    "password",
    "oauth",
    "user",
    "credential",
    "middleware",
    "signup",
    "sign-in",
    "signin",
)


class PatchGenerationError(Exception):
    """Raised when a real patch cannot be produced."""

    def __init__(
        self,
        message: str,
        raw_completion: str | None = None,
        quality_gate: dict[str, object] | None = None,
        *,
        first_attempt_latency: float | None = None,
        retry_latency: float | None = None,
        raw_structured_ok: bool = False,
        structured_recovery: bool = False,
        recovery_failed: bool = False,
    ):
        super().__init__(message)
        self.raw_completion = raw_completion
        self.quality_gate = quality_gate
        self.first_attempt_latency = first_attempt_latency
        self.retry_latency = retry_latency
        self.raw_structured_ok = raw_structured_ok
        self.structured_recovery = structured_recovery
        self.recovery_failed = recovery_failed


def is_health_request(request: str) -> bool:
    lowered = request.lower()
    return "health" in lowered and any(
        term in lowered for term in ("endpoint", "route", "api", "/health", "healthcheck", "health check")
    )


def is_todo_only_content(original: str | None, new_content: str) -> bool:
    """True when the new file is effectively only Otter TODO comments vs original."""
    if not TODO_MARKER_RE.search(new_content):
        return False
    # Strip Otter TODO comment lines and compare to original
    stripped_lines: list[str] = []
    for line in new_content.splitlines():
        stripped = line.strip()
        if TODO_MARKER_RE.search(stripped):
            continue
        if stripped in {
            "// Implement carefully and remove this marker when done.",
            "# Implement carefully and remove this marker when done.",
        }:
            continue
        stripped_lines.append(line)
    cleaned = "\n".join(stripped_lines).strip()
    baseline = (original or "").strip()
    if cleaned == baseline:
        return True
    # Brand-new file that is only TODO comments
    non_empty = [line for line in cleaned.splitlines() if line.strip()]
    if not baseline and not non_empty:
        return True
    if not baseline and all(
        line.strip().startswith(("//", "#", "/*", "*")) or not line.strip() for line in new_content.splitlines()
    ):
        return True
    return False


def is_todo_only_patch(
    files: list[dict[str, str]],
    originals: dict[str, str] | None = None,
) -> bool:
    """True if every changed file is a TODO-only stub."""
    if not files:
        return True
    originals = originals or {}
    todoish = 0
    for item in files:
        path = item.get("path", "")
        content = str(item.get("content") or "")
        if is_todo_only_content(originals.get(path), content):
            todoish += 1
        elif TODO_MARKER_RE.search(content) and "Implement carefully" in content:
            # Fallback-style addition even if we can't prove noop vs original
            todoish += 1
        else:
            return False
    return todoish == len(files)


_AUTH_REQUEST_TERMS = {
    "login",
    "password",
    "signup",
    "signin",
    "sign-up",
    "sign-in",
    "oauth",
    "credential",
    "credentials",
}
_AUTH_ACCOUNT_TERMS = {"user", "users", "account", "accounts", "identity"}
_PASSWORD_HASH_MARKERS = (
    "bcrypt",
    "argon2",
    "scrypt",
    "pbkdf2",
    "hashpassword",
    "hash_password",
    "passwordhash",
    "crypto.createhash",
    "crypto.scrypt",
    "crypto.pbkdf2",
    "bcryptjs",
    "hashpw",
)
_FAKE_ORM_MARKERS = (
    "@drizzle/driver",
    "pgdriver",
    ".addcolumns(",
    "db.schema(",
    "drizzle(pgdriver)",
    ".database('mydb')",
    '.database("mydb")',
)
_NODE_CORE = {
    "assert",
    "buffer",
    "child_process",
    "crypto",
    "events",
    "fs",
    "http",
    "https",
    "net",
    "os",
    "path",
    "process",
    "querystring",
    "readline",
    "stream",
    "timers",
    "tls",
    "url",
    "util",
    "zlib",
    "node:assert",
    "node:buffer",
    "node:child_process",
    "node:crypto",
    "node:fs",
    "node:http",
    "node:https",
    "node:os",
    "node:path",
    "node:url",
    "node:util",
}
_IMPORT_RE = re.compile(
    r"""(?:from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\))"""
)

# Sensible default versions when the model imports a package but forgets dependencies{}.
DEFAULT_DEP_VERSIONS: dict[str, str] = {
    "bcrypt": "^5.1.1",
    "bcryptjs": "^2.4.3",
    "@types/bcrypt": "^5.0.2",
    "@types/bcryptjs": "^2.4.6",
    "uuid": "^11.0.3",
    "@types/uuid": "^10.0.0",
    "argon2": "^0.41.1",
    "jsonwebtoken": "^9.0.2",
    "@types/jsonwebtoken": "^9.0.7",
    "passport": "^0.7.0",
    "passport-local": "^1.0.0",
    "@types/passport": "^1.0.17",
    "@types/passport-local": "^1.0.38",
    "express-session": "^1.18.1",
    "@types/express-session": "^1.18.0",
    "zod": "^3.24.1",
}



def _is_auth_request(request: str) -> bool:
    """True for credential/login work, not 'register the route' or HTTP Basic copy tweaks."""
    lowered = request.lower()
    if "email/password" in lowered or "email and password" in lowered:
        return True
    words = set(re.findall(r"[a-z0-9_-]+", lowered))
    if words & _AUTH_REQUEST_TERMS:
        return True
    if "register" in words and words & _AUTH_ACCOUNT_TERMS:
        if words & {"password", "login", "signup", "signin", "account"}:
            return True
        if not words & {"route", "routes", "endpoint", "router", "app"}:
            return True
    return False


_LLM_SUMMARY_PREFIX_RE = re.compile(r"^\[llm:[^\]]+\]\s*", re.IGNORECASE)
_AUTH_STUB_MARKERS = (
    "replace with actual",
    "implement later",
    "implementation todo",
    "todo(otter)",
    "add real user lookup",
    "placeholder auth",
)
_NON_USER_AUTH_TABLES = ("cards", "card", "greetings", "messages", "posts", "orders")


def strip_llm_summary_prefix(text: str) -> str:
    """Remove legacy `[llm:model]` prefixes from user-facing summaries / PR bodies."""
    cleaned = str(text or "").strip()
    while True:
        nxt = _LLM_SUMMARY_PREFIX_RE.sub("", cleaned).strip()
        if nxt == cleaned:
            return cleaned
        cleaned = nxt


def _package_names_from_json(text: str) -> set[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = data.get(key) or {}
        if isinstance(section, dict):
            names.update(str(name) for name in section)
    return names


def _known_packages(files: list[dict[str, str]], originals: dict[str, str]) -> set[str]:
    known: set[str] = set(_NODE_CORE)
    for source in list(originals.values()) + [item.get("content", "") for item in files]:
        if '"dependencies"' in source or "'dependencies'" in source:
            known |= _package_names_from_json(source)
    # Path aliases / relative imports already used in the repo
    for source in originals.values():
        for match in _IMPORT_RE.finditer(source):
            spec = next((group for group in match.groups() if group), "")
            if spec.startswith(".") or spec.startswith("@shared") or spec.startswith("@/"):
                known.add(spec.split("/")[0] if not spec.startswith(".") else spec)
                if spec.startswith("@") and "/" in spec:
                    known.add("/".join(spec.split("/")[:2]))
    return known


def _imported_packages(content: str) -> set[str]:
    found: set[str] = set()
    for match in _IMPORT_RE.finditer(content):
        spec = next((group for group in match.groups() if group), "")
        if not spec or spec.startswith(".") or spec.startswith("/"):
            continue
        if spec.startswith("node:"):
            found.add(spec)
            continue
        if spec.startswith("@"):
            parts = spec.split("/")
            found.add("/".join(parts[:2]) if len(parts) >= 2 else spec)
        else:
            found.add(spec.split("/")[0])
    return found


def validate_patch_quality(
    request: str,
    files: list[dict[str, str]],
    originals: dict[str, str] | None = None,
) -> None:
    """Reject hallucinated / obviously broken patches before they can be applied."""
    originals = originals or {}
    if not files:
        raise ValueError("Patch contained no files")
    if is_todo_only_patch(files, originals):
        raise ValueError("Patch is TODO-only; refusing stub markers as a successful generation")

    joined = "\n".join(str(item.get("content") or "") for item in files)
    joined_l = joined.lower()
    known = _known_packages(files, originals)
    problems: list[str] = []

    for marker in _FAKE_ORM_MARKERS:
        if marker in joined_l:
            problems.append(f"invented ORM/API usage (`{marker}`)")
            break
    if re.search(r"""\.from\(\s*['"][a-z0-9_]+['"]\s*\)""", joined_l):
        problems.append("Drizzle/SQL `.from('tableName')` string API (use table objects from schema)")

    for item in files:
        path = str(item.get("path") or "")
        content = str(item.get("content") or "")
        original = originals.get(path, "")
        if "pgTable(" in original and "pgTable(" not in content and path.endswith(("schema.ts", "schema.js")):
            problems.append(f"`{path}` removed existing drizzle `pgTable` definitions")
        if "drizzle-orm/node-postgres" in original and "drizzle-orm/node-postgres" not in content and path.endswith("db.ts"):
            problems.append(f"`{path}` replaced the existing drizzle/node-postgres setup")
        if "drizzle-orm/pg-core" in original and "drizzle-orm/pg-core" not in content and "schema" in path:
            problems.append(f"`{path}` dropped drizzle-orm/pg-core imports")

        for pkg in _imported_packages(content):
            if pkg.startswith("@shared") or pkg.startswith("@/"):
                continue
            root = pkg
            if root not in known and not any(root == k or k.startswith(root + "/") for k in known):
                # Allow packages already imported elsewhere in context
                if any(root in src for src in originals.values()):
                    continue
                problems.append(f"imports `{pkg}` but it is not in package.json / known repo packages")

    if _is_auth_request(request):
        has_hash = any(marker in joined_l for marker in _PASSWORD_HASH_MARKERS)
        if not has_hash:
            problems.append("auth change does not hash passwords (need bcrypt/argon2/scrypt/pbkdf2)")
        if re.search(r"hashed\s*password\s*=\s*password\b", joined_l) or re.search(
            r"password\s*:\s*password\b", joined_l
        ):
            problems.append("stores plaintext password instead of a hash")
        if re.search(r"\.password\s*!==\s*password\b", joined_l) or re.search(
            r"\.password\s*===\s*password\b", joined_l
        ):
            if not has_hash:
                problems.append("compares raw passwords without a password hash verify")
        for marker in _AUTH_STUB_MARKERS:
            if marker in joined_l:
                problems.append(f"auth stub language (`{marker}`)")
                break
        auth_route = bool(
            re.search(r"""(?:app|router)\.(post|put)\(['"][^'"]*(login|register|signup|signin|auth)""", joined_l)
            or re.search(r"""['"]/(api/)?(login|register|signup|signin|auth)""", joined_l)
        )
        users_table = _has_users_model(joined, originals)
        if not auth_route:
            problems.append("auth change is missing login/register routes")
        if not users_table:
            problems.append("auth change is missing a users model/table (do not reuse domain tables like cards)")
        for table in _NON_USER_AUTH_TABLES:
            if re.search(rf"""\.from\(\s*{table}\s*\)""", joined_l) or re.search(
                rf"""{table}\.(recipientname|email|password)""", joined_l
            ):
                problems.append(f"auth lookup against non-user table `{table}`")
                break
        uses_session = bool(re.search(r"req\.session\b", joined) or re.search(r"request\.session\b", joined))
        if uses_session:
            session_ok = any(
                name in known
                for name in ("express-session", "cookie-session", "iron-session", "next-auth", "passport")
            )
            if not session_ok:
                problems.append(
                    "uses req.session without express-session / passport / next-auth (or equivalent) in dependencies"
                )
        if re.search(r"""\.select\s*\([^)]*\)[\s\S]{0,180}?\.get\s*\(""", joined):
            problems.append("invalid Drizzle chain `.select(...).get()` (node-postgres drizzle has no .get())")

    # Deduplicate while preserving order
    unique: list[str] = []
    for problem in problems:
        if problem not in unique:
            unique.append(problem)
    if unique:
        from packages.agent.patch import QualityGateError

        category = "invented_architecture" if any("invented" in p or "ORM" in p or "drizzle" in p.lower() for p in unique) else "low_quality"
        if any("package.json" in p or "imports `" in p for p in unique):
            category = "unexpected_dependency"
        if any("auth " in p for p in unique):
            category = "incomplete_auth"
        raise QualityGateError(category, "; ".join(unique[:6]))


_USER_DOMAIN_MARKERS = (
    "userrepository",
    "userservice",
    "insertuser",
    "createuser",
    "interface user",
    "type user ",
    "type user=",
    "class user",
)


def _has_users_model(joined: str, originals: dict[str, str]) -> bool:
    if re.search(r"""pgTable\(\s*['"]users['"]""", joined):
        return True
    if re.search(r"""(?:export\s+)?const\s+users\s*=""", joined):
        return True
    if re.search(r"""class\s+User\b""", joined):
        return True
    if re.search(r"""__tablename__\s*=\s*['"]users['"]""", joined):
        return True
    orig = "\n".join(originals.values()).lower()
    if any(marker in orig for marker in _USER_DOMAIN_MARKERS) and (
        "passwordhash" in joined.lower() or "password_hash" in joined.lower()
    ):
        return True
    return False


def _repair_triple_quoted_json(text: str) -> str:
    """Turn Python-style triple-quoted JSON values into valid JSON strings."""

    def repl(match: re.Match[str]) -> str:
        return f'"{match.group("key")}": {json.dumps(match.group("body"))}'

    return re.sub(
        r'"(?P<key>old_string|new_string|content|summary)"\s*:\s*"""(?P<body>[\s\S]*?)"""',
        repl,
        text,
    )


def _repair_json_text(text: str) -> str:
    repaired = _repair_triple_quoted_json(text)
    if repaired != text:
        return repaired
    return text


def _salvage_array_objects(text: str, key: str) -> list[dict]:
    token = f'"{key}"'
    key_at = text.find(token)
    if key_at == -1:
        return []
    files_start = text.find("[", key_at)
    if files_start == -1:
        return []
    decoder = json.JSONDecoder()
    entries: list[dict] = []
    index = files_start + 1
    while index < len(text):
        brace = text.find("{", index)
        if brace == -1:
            break
        try:
            entry, offset = decoder.raw_decode(text, brace)
        except ValueError:
            break
        if isinstance(entry, dict):
            entries.append(entry)
        index = offset
    return entries


def _salvage_truncated_json(text: str) -> dict | None:
    """Recover whole `files[]` entries from a response cut off mid-generation.

    Groq returns the partial completion in `failed_generation`; everything before the
    truncation point is still a usable patch, so keep the complete entries.
    """
    decoder = json.JSONDecoder()
    summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    files_start = text.find("[", text.find('"files"')) if '"files"' in text else -1
    entries: list[dict[str, str]] = []
    if files_start != -1:
        index = files_start + 1
        while index < len(text):
            brace = text.find("{", index)
            if brace == -1:
                break
            try:
                entry, offset = decoder.raw_decode(text, brace)
            except ValueError:
                break
            if isinstance(entry, dict) and entry.get("path") and entry.get("content") is not None:
                entries.append(entry)
            index = offset
    edits = _salvage_array_objects(text, "edits") or _salvage_array_objects(text, "changes")
    if not entries and not edits:
        return None
    summary = summary_match.group(1) if summary_match else "Recovered partial patch"
    recovered: dict[str, object] = {
        "summary": json.loads(f'"{summary}"'),
        "_local_repair": True,
    }
    if edits:
        recovered["edits"] = edits
    if entries and not edits:
        recovered["files"] = entries
        recovered["truncated"] = True
    elif entries and edits:
        # Keep only complete files[] entries when edits already carry the change.
        complete = [
            item
            for item in entries
            if isinstance(item, dict) and item.get("path") and item.get("content") is not None
        ]
        if complete:
            recovered["files"] = complete
    return recovered


def _strip_code_fences(text: str) -> str:
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _try_load_json_dict(text: str) -> dict | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start != -1:
        try:
            data, _end = decoder.raw_decode(text, start)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _extract_json_object(content: str) -> dict:
    text = _strip_code_fences(content or "")
    data = _try_load_json_dict(text)
    if data is not None:
        return data
    repaired = _repair_json_text(text)
    if repaired != text:
        data = _try_load_json_dict(repaired)
        if data is not None:
            data["_local_repair"] = True
            return data
        text = repaired
    stripped_commas = re.sub(r",\s*([}\]])", r"\1", text)
    if stripped_commas != text:
        data = _try_load_json_dict(stripped_commas)
        if data is not None:
            data["_local_repair"] = True
            return data
        text = stripped_commas
    salvaged = _salvage_truncated_json(text)
    if salvaged is not None:
        return salvaged
    raise ValueError("No JSON object found in model response")


def _merge_dependencies(manifest: str, additions: dict[str, str]) -> str | None:
    """Apply a dependency delta to package.json, preserving formatting style."""
    try:
        data = json.loads(manifest)
    except json.JSONDecodeError:
        # Truncated context can leave invalid JSON — salvage the dependencies object if present.
        match = re.search(r'"dependencies"\s*:\s*\{', manifest)
        if not match or not additions:
            return None
        # Build a minimal manifest from salvaged keys + additions.
        existing: dict[str, str] = {}
        for name, version in re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', manifest[match.end() : match.end() + 8000]):
            if name in {"name", "version", "private", "type"}:
                continue
            existing[name] = version
            if len(existing) > 200:
                break
        data = {"dependencies": existing}
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        deps = {}
        data["dependencies"] = deps
    changed = False
    for name, version in additions.items():
        name = str(name).strip()
        if not name or name in deps:
            continue
        deps[name] = str(version).strip() or "latest"
        changed = True
    if not changed:
        return None
    data["dependencies"] = dict(sorted(deps.items()))
    return json.dumps(data, indent=2) + "\n"


def _missing_npm_imports(
    files: list[dict[str, str]],
    originals: dict[str, str],
    already: dict[str, str] | None = None,
) -> dict[str, str]:
    """Infer package.json additions from imports the model used but did not declare."""
    known = _known_packages(files, originals)
    known |= set((already or {}).keys())
    missing: dict[str, str] = {}
    for item in files:
        for pkg in _imported_packages(str(item.get("content") or "")):
            if pkg.startswith((".", "/", "node:", "@shared", "@/")):
                continue
            if pkg in known or any(pkg == k or k.startswith(pkg + "/") for k in known):
                continue
            # Skip path aliases that look like local packages
            if pkg.startswith("@") and pkg.count("/") == 0:
                continue
            missing[pkg] = DEFAULT_DEP_VERSIONS.get(pkg, "latest")
            known.add(pkg)
    return missing


def _strip_otter_stub_files(files: list[dict[str, str]]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for item in files:
        path = str(item.get("path") or "").replace("\\", "/")
        lowered = path.lower()
        name = Path(path).name.lower()
        if lowered.startswith("otter_") or name in {"otter_health.py", "otter_change_request.md"}:
            continue
        if name in MANIFEST_PATHS or lowered in MANIFEST_PATHS:
            continue
        kept.append(item)
    return kept


def _explicit_dependency_delta(result: dict, originals: dict[str, str]) -> dict[str, str]:
    """Only packages the model declared, not inferred from imports."""
    declared: dict[str, str] = {}
    raw_deps = result.get("dependencies")
    if isinstance(raw_deps, dict):
        declared.update({str(k): str(v) for k, v in raw_deps.items() if str(k).strip()})
    for item in result.get("files") or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").replace("\\", "/").lower()
        if path == "package.json" or Path(path).name == "package.json":
            declared.update(_package_dependency_delta(originals.get("package.json", ""), str(item.get("content") or "")))
    existing = _package_names_from_json(originals.get("package.json", ""))
    return {name: spec for name, spec in declared.items() if name not in existing}


def _normalize_patch(
    result: dict,
    *,
    originals: dict[str, str] | None = None,
    request: str = "",
    excerpts: dict[str, str] | None = None,
) -> dict[str, object]:
    originals = originals or {}
    summary = strip_llm_summary_prefix(str(result.get("summary") or "").strip())
    local_repair = bool(result.pop("_local_repair", False))
    if result.get("truncated") and not result.get("edits") and not result.get("changes"):
        from packages.agent.patch import QualityGateError

        raise QualityGateError("truncated_patch", "Truncated patch JSON; refusing partial full-file salvage. Use edits.")
    if result.get("truncated") and (result.get("edits") or result.get("changes")):
        result = dict(result)
        result["files"] = []
        result["truncated"] = False
        local_repair = True
    if not summary:
        raise ValueError("Invalid patch shape: missing summary")

    new_deps = _explicit_dependency_delta(result, originals)
    payload = dict(result)
    payload["files"] = [
        item
        for item in (result.get("files") or [])
        if isinstance(item, dict)
        and Path(str(item.get("path") or "")).name.lower() not in MANIFEST_PATHS
    ]
    try:
        from packages.agent.patch import materialize_safe_patch

        normalized_files = _strip_otter_stub_files(
            materialize_safe_patch(payload, originals, excerpts=excerpts)
        )
    except ValueError:
        raise
    except Exception as error:  # noqa: BLE001
        raise ValueError(f"Invalid patch shape: {error}") from error

    js_stack = _is_js_patch(normalized_files, originals)
    if new_deps and js_stack:
        base_manifest = originals.get("package.json") or '{"name":"app","dependencies":{}}'
        merged = _merge_dependencies(base_manifest, new_deps)
        if merged is not None:
            normalized_files = [item for item in normalized_files if item["path"] != "package.json"]
            normalized_files.append({"path": "package.json", "content": merged})

    if not normalized_files:
        raise ValueError("Invalid patch shape: missing files/edits")
    validate_patch_quality(request, normalized_files, originals)
    return {
        "summary": summary,
        "files": normalized_files,
        "source": "llm",
        "truncated": False,
        "_local_repair": local_repair,
    }


def _is_retryable_validation_error(error: BaseException | str) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.ConnectError)):
        return False
    text = str(error).lower()
    if any(marker in text for marker in ("timed out", "timeout", "connect", "10061", "network")):
        return False
    if "http 5" in text or "http 429" in text:
        return False
    return True


def _retry_user_message(error: str, excerpts: dict[str, str] | None = None) -> str:
    """Compact structural repair. Never resend repository context."""
    del excerpts
    return _json_repair_user_message(error, "")


def _json_repair_user_message(error: str, raw: str) -> str:
    preview = (raw or "")[:2000]
    return (
        f"STRUCTURAL JSON ERROR:\n{error}\n\n"
        "Fix formatting only. Do not change the intended code.\n"
        "Return ONLY JSON. No markdown. No code fences. No repository files.\n"
        '{"summary":"...","edits":[{"path":"...","symbol":"...","old_string":"...","new_string":"..."}]}\n'
        + (f"Previous response to repair:\n{preview}\n" if preview else "")
    )


def _syntax_repair_user_message(error: str, broken_files: list[dict[str, str]]) -> str:
    blocks = []
    for item in broken_files[:3]:
        body = str(item.get("content") or "")[:2500]
        blocks.append(f"BROKEN FILE: {item.get('path')}\n{body}")
    return (
        f"PYTHON SYNTAX ERROR:\n{error}\n\n"
        "Fix only the syntax in the broken generated file(s). Do not rewrite unrelated code.\n"
        "Return ONLY JSON. No markdown.\n"
        '{"summary":"...","files":[{"path":"...","content":"..."}]}\n\n'
        + "\n\n".join(blocks)
    )


_GATE_NO_RETRY = {
    "destructive_rewrite",
    "incomplete_auth",
    "unexpected_dependency",
    "edit_target_not_found",
    "edit_target_not_unique",
    "ambiguous_anchor",
    "invented_architecture",
    "low_quality",
    "missing_files_edits",
    "truncated_patch",
}


def _format_llm_error(model_id: str, error: object, *, timeout_s: float | None = None) -> str:
    if isinstance(error, httpx.TimeoutException):
        seconds = f" after {timeout_s:.0f}s" if timeout_s else ""
        detail = str(error).strip()
        return f"{model_id} timed out{seconds}" + (f": {detail}" if detail else "")
    reason = str(error).strip() if error is not None else ""
    if not reason:
        reason = type(error).__name__ if not isinstance(error, str) else "empty error"
    return f"{model_id}: {reason}"


def _is_js_patch(files: list[dict[str, str]], originals: dict[str, str]) -> bool:
    js_exts = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    paths = [str(item.get("path") or "") for item in files] + list(originals)
    if any(Path(path).suffix.lower() in js_exts for path in paths):
        return True
    return any(Path(path).name.lower() == "package.json" for path in originals)


def _package_names_as_deps(manifest: str) -> dict[str, str]:
    names = _package_names_from_json(manifest)
    return {name: "latest" for name in names}

def _package_dependency_delta(original: str, proposed: str) -> dict[str, str]:
    """Extract only the dependencies a rewritten package.json would add."""
    before = _package_names_from_json(original)
    try:
        data = json.loads(proposed)
    except json.JSONDecodeError:
        return {}
    additions: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            for name, version in section.items():
                if str(name) not in before:
                    additions[str(name)] = str(version)
    return additions


def _score_file(path: str, request: str) -> float:
    words = set(re.findall(r"[a-z0-9_]+", request.lower()))
    lowered = path.lower()
    score = 0.0
    for word in words:
        if len(word) > 2 and word in lowered:
            score += 3.0
    basename = Path(lowered).name
    if basename in {
        "main.py",
        "app.py",
        "server.py",
        "index.ts",
        "index.js",
        "server.ts",
        "server.js",
        "route.ts",
        "routes.ts",
        "app.ts",
        "app.js",
    }:
        score += 4.0
    if "health" in words and "health" in lowered:
        score += 10.0
    if any(term in words for term in ("auth", "login", "password", "session", "oauth", "signup", "signin")):
        if any(term in lowered for term in AUTH_PATH_TERMS):
            score += 8.0
    if any(part in lowered for part in ("/api/", "routes/", "router", "controllers/", "auth/", "middleware/")):
        score += 2.0
    if lowered.endswith((".md", ".json", ".lock")):
        score -= 5.0
    return score


def _pick_targets(files: list[dict[str, str]], request: str, *, limit: int = 5) -> list[dict[str, str]]:
    ranked = sorted(((_score_file(item["path"], request), item) for item in files), key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked if score > 0][:limit] or files[:limit]


def _find_existing_health(files: list[dict[str, str]]) -> dict[str, str] | None:
    for item in files:
        content = item["content"]
        path = item["path"].lower()
        if "health" in path and path.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".go")):
            return item
        if any(pattern.search(content) for pattern in HEALTH_PATTERNS):
            return item
        if re.search(r"\bhealth\b", content, re.I) and (
            "endpoint" in content.lower() or "route" in content.lower() or "@app.get" in content or "router." in content
        ):
            return item
    return None


def _detect_stack(files: list[dict[str, str]]) -> str:
    paths = " ".join(item["path"].lower() for item in files)
    joined = "\n".join(item["content"][:2000] for item in files[:8])
    if "next" in joined.lower() or "app/api/" in paths or "pages/api/" in paths:
        return "next"
    if "fastapi" in joined.lower() or "from fastapi" in joined:
        return "fastapi"
    if "express" in joined.lower() or "from flask" in joined.lower():
        return "node_or_flask"
    if any(item["path"].endswith(".py") for item in files):
        return "python"
    if any(item["path"].endswith((".ts", ".tsx", ".js", ".jsx")) for item in files):
        return "node"
    return "unknown"


def _health_patch_for_stack(stack: str, files: list[dict[str, str]], request: str) -> dict[str, object]:
    existing = _find_existing_health(files)
    if existing:
        return {
            "summary": (
                f"[deterministic] A health surface already exists in `{existing['path']}`. "
                "No duplicate route was added to avoid conflicts. Review that file before changing behavior."
            ),
            "files": [{"path": existing["path"], "content": existing["content"]}],
            "noop": True,
            "source": "deterministic",
        }

    if stack == "next":
        has_app_dir = any(item["path"].startswith("app/") for item in files)
        if has_app_dir or not any(item["path"].startswith("pages/") for item in files):
            path = "app/api/health/route.ts"
            content = (
                'import { NextResponse } from "next/server";\n\n'
                "export async function GET() {\n"
                '  return NextResponse.json({ status: "ok" });\n'
                "}\n"
            )
            return {
                "summary": "[deterministic] Adds a Next.js App Router health endpoint at `app/api/health/route.ts`.",
                "files": [{"path": path, "content": content}],
                "source": "deterministic",
            }
        path = "pages/api/health.ts"
        content = (
            'import type { NextApiRequest, NextApiResponse } from "next";\n\n'
            "export default function handler(_req: NextApiRequest, res: NextApiResponse) {\n"
            '  res.status(200).json({ status: "ok" });\n'
            "}\n"
        )
        return {
            "summary": "[deterministic] Adds a Next.js Pages Router health endpoint at `pages/api/health.ts`.",
            "files": [{"path": path, "content": content}],
            "source": "deterministic",
        }

    if stack == "fastapi":
        targets = _pick_targets(files, "fastapi main app route health")
        target = next((item for item in targets if item["path"].endswith(".py")), None)
        if target and ("FastAPI" in target["content"] or "@app." in target["content"]):
            if "/health" in target["content"]:
                return {
                    "summary": f"[deterministic] `{target['path']}` already references health; left unchanged.",
                    "files": [{"path": target["path"], "content": target["content"]}],
                    "noop": True,
                    "source": "deterministic",
                }
            addition = (
                '\n\n@app.get("/health")\n'
                "async def health() -> dict[str, str]:\n"
                '    return {"status": "ok"}\n'
            )
            return {
                "summary": f"[deterministic] Adds a FastAPI `/health` route to `{target['path']}`.",
                "files": [{"path": target["path"], "content": target["content"].rstrip() + addition + "\n"}],
                "source": "deterministic",
            }

    if stack in {"node", "node_or_flask"}:
        targets = _pick_targets(files, request + " server index app routes")
        target = next((item for item in targets if item["path"].endswith((".ts", ".js"))), None)
        if target:
            content = target["content"]
            if "/health" in content:
                return {
                    "summary": f"[deterministic] `{target['path']}` already exposes health; left unchanged.",
                    "files": [{"path": target["path"], "content": content}],
                    "noop": True,
                    "source": "deterministic",
                }
            if "express" in content.lower() or "app.get" in content or "router.get" in content:
                addition = (
                    '\n\napp.get("/health", (_req, res) => {\n'
                    '  res.status(200).json({ status: "ok" });\n'
                    "});\n"
                )
                return {
                    "summary": f"[deterministic] Adds an Express-style `/health` route to `{target['path']}`.",
                    "files": [{"path": target["path"], "content": content.rstrip() + addition + "\n"}],
                    "source": "deterministic",
                }

    if any(item["path"].endswith((".ts", ".tsx", ".js", ".jsx")) for item in files):
        path = "app/api/health/route.ts"
        content = (
            'import { NextResponse } from "next/server";\n\n'
            "export async function GET() {\n"
            '  return NextResponse.json({ status: "ok" });\n'
            "}\n"
        )
        return {
            "summary": "[deterministic] Adds `app/api/health/route.ts` following common Next.js API conventions.",
            "files": [{"path": path, "content": content}],
            "source": "deterministic",
        }
    path = "api/health.py"
    content = (
        '"""Health route module — wire into your app router if not auto-discovered."""\n\n'
        "def health() -> dict[str, str]:\n"
        '    return {"status": "ok"}\n'
    )
    return {
        "summary": "[deterministic] Adds `api/health.py` as a conventional health module for review and wiring.",
        "files": [{"path": path, "content": content}],
        "source": "deterministic",
    }


def deterministic_patch(request: str, files: list[dict[str, str]]) -> dict[str, object]:
    """Deterministic patches are allowed only for health endpoints — never TODO stubs."""
    if is_health_request(request):
        return _health_patch_for_stack(_detect_stack(files), files, request)
    raise PatchGenerationError(
        "Deterministic fallback cannot implement this request. "
        "Start Ollama with qwen2.5-coder:7b (or set LLM_MODEL), then regenerate."
    )


def _is_ollama_base(base_url: str) -> bool:
    lowered = (base_url or "").lower()
    return any(
        marker in lowered
        for marker in ("11434", "host.docker.internal", "localhost", "127.0.0.1", "ollama")
    )


def _resolve_base_url(base_url: str) -> str:
    """Prefer IPv4 for host.docker.internal — httpx often picks broken IPv6 in Docker Desktop."""
    if "host.docker.internal" not in (base_url or "").lower():
        return base_url

    try:
        infos = socket.getaddrinfo("host.docker.internal", 11434, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        return base_url
    if not infos:
        return base_url
    ipv4 = infos[0][4][0]
    return base_url.replace("host.docker.internal", ipv4).replace("Host.docker.internal", ipv4)


def _validate_llm_settings() -> tuple[str, str, str]:
    from app.llm_settings import get_effective_runtime_sync

    runtime = get_effective_runtime_sync()
    key = (runtime.api_key or "").strip()
    model = (runtime.model or "").strip()
    base = (runtime.base_url or "").strip()
    if not base:
        raise PatchGenerationError(
            "LLM base URL is not set. Open Models and choose Local Ollama "
            "(http://host.docker.internal:11434/v1 in Docker)."
        )
    if not key and not _is_ollama_base(base):
        raise PatchGenerationError(
            "LLM API key is not set. For local Ollama leave it empty; for OpenAI-compatible providers set a key in Models."
        )
    if model.lower() in PLACEHOLDER_MODELS:
        raise PatchGenerationError(
            f"LLM model `{model or '(empty)'}` is a placeholder. "
            "Open Models and pick a local Ollama tag such as qwen2.5-coder:7b."
        )
    if not key and _is_ollama_base(base):
        key = "ollama"
    return key, model, base


def _free_model_candidates(primary: str, *, free_failover: bool) -> list[str]:
    """Build an ordered list of local models to try for coding."""
    primary = (primary or "").strip()
    if free_failover or primary in FREE_CODING_MODELS:
        ordered: list[str] = []
        if primary:
            ordered.append(primary)
        for mid in FREE_CODING_MODELS:
            if mid not in ordered:
                ordered.append(mid)
        return ordered
    return [primary]


def _llm_headers(api_key: str, base_url: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key or 'ollama'}",
        "Content-Type": "application/json",
    }
    if "openrouter.ai" in base_url:
        settings = get_settings()
        headers["HTTP-Referer"] = settings.next_public_url or "http://localhost:3000"
        headers["X-Title"] = "Otter"
    return headers


def _supports_json_object(base_url: str) -> bool:
    # Local Ollama tags often fail or truncate under strict json_object mode.
    if _is_ollama_base(base_url):
        return False
    return any(host in base_url for host in ("openai.com", "openrouter.ai", "api.groq.com"))


def _failed_generation_text(response: httpx.Response) -> str:
    """Some providers return the partial completion alongside a JSON validation error."""
    try:
        error = response.json().get("error") or {}
    except (json.JSONDecodeError, ValueError):
        return ""
    if error.get("code") != "json_validate_failed":
        return ""
    return str(error.get("failed_generation") or "")


async def generate_patch(
    request: str,
    files: list[dict[str, str]],
    *,
    plan_context: dict[str, object] | None = None,
    apply_originals: dict[str, str] | None = None,
) -> dict[str, object]:
    """Generate a real patch via LLM, or a deterministic health patch. Never TODO stubs."""
    excerpts = {item["path"]: item["content"] for item in files}
    originals = dict(apply_originals) if apply_originals else dict(excerpts)
    for path, body in excerpts.items():
        originals.setdefault(path, body)
    settings = get_settings()

    # Health can still use deterministic path when LLM is unavailable
    if is_health_request(request):
        try:
            key, model, base = _validate_llm_settings()
        except PatchGenerationError:
            return deterministic_patch(request, files)
    else:
        key, model, base = _validate_llm_settings()

    limited = files[:CONTEXT_FILE_LIMIT]
    target_paths = [item["path"] for item in limited]
    context = "\n\n".join(
        f"FILE: {item['path']}\n{item['content'][:CONTEXT_CHARS_PER_FILE]}" for item in limited
    )
    plan_files = []
    if plan_context:
        plan_files = [
            str(path)
            for path in (plan_context.get("affected_files") or [])
            if str(path) in set(target_paths)
        ][:6]
    auth_rules = ""
    if _is_auth_request(request):
        auth_rules = (
            "Auth: keep the existing user repository/model; add passwordHash; hash with node:crypto "
            "or a declared dependencies{} package; add real login/register routes. "
            "No plaintext, no TODOs, no invented ORM APIs.\n"
        )
    prompt = (
        "SYSTEM TASK: smallest correct change to an existing repository.\n"
        "Return ONLY JSON. No markdown. No fences. No prose.\n"
        '{"summary":"...","edits":[{"path":"...","symbol":"...","old_string":"...","new_string":"..."}],'
        '"files":[{"path":"...","content":"..."}],"dependencies":{}}\n'
        "Rules:\n"
        "- Existing files: edits only. symbol = unique function/class/const name.\n"
        "- old_string = shortest unique snippet inside that symbol; copy quotes exactly.\n"
        "- old_string \"\" appends at end of file (or after symbol when symbol is set).\n"
        "- files[] ONLY for brand-new paths not in TARGET FILES. Never rewrite an existing file.\n"
        "- Never paste a whole existing test module. Add tests with edits.\n"
        "- Preserve unrelated code and functions. No TODOs. No package.json bodies.\n"
        "- New npm imports: put the package in dependencies{}. Prefer node:crypto for hashing.\n"
        f"{auth_rules}"
        f"TASK:\n{request}\n"
        f"TARGET FILES: {json.dumps(target_paths)}\n"
        f"PLAN FILES: {json.dumps(plan_files)}\n"
        f"RELEVANT CODE:\n{context}\n"
        "OUTPUT: JSON only."
    )

    free_failover = bool(getattr(settings, "llm_free_failover", True))
    try:
        from app.llm_settings import get_effective_runtime_sync

        free_failover = get_effective_runtime_sync().free_failover
    except Exception:  # noqa: BLE001
        pass
    if _is_ollama_base(base):
        free_failover = True
    candidates = _free_model_candidates(model, free_failover=free_failover)
    last_error = "unknown LLM error"
    last_raw = ""
    local = _is_ollama_base(base)
    timeout = 180.0 if local else 120.0
    request_base = _resolve_base_url(base)
    first_attempt_latency: float | None = None
    retry_latency: float | None = None

    async def _post_completion(payload: dict[str, object]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(
                f"{request_base.rstrip('/')}/chat/completions",
                headers=_llm_headers(key, base),
                json=payload,
            )

    def _parse_and_normalize(text: str) -> dict[str, object]:
        parsed = _extract_json_object(text)
        patch = _normalize_patch(
            parsed, originals=originals, request=request, excerpts=excerpts
        )
        patch["summary"] = strip_llm_summary_prefix(str(patch["summary"]))
        return patch

    for model_id in candidates:
        payload: dict[str, object] = {
            "model": model_id,
            "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior software engineer modifying an existing repository. "
                        "Return only compact JSON: summary plus edits (and files[] only for new paths). "
                        "Use symbol + short unique old_string. Preserve existing code. "
                        "Never rewrite a whole file. No markdown. No package.json. No TODOs."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if not local:
            payload["max_completion_tokens"] = MAX_COMPLETION_TOKENS
        else:
            payload["options"] = {"num_ctx": OLLAMA_NUM_CTX, "num_predict": MAX_COMPLETION_TOKENS}
        if _supports_json_object(base):
            payload["response_format"] = {"type": "json_object"}

        try:
            attempt_started = time.perf_counter()
            response = await _post_completion(payload)
            first_attempt_latency = time.perf_counter() - attempt_started
            if response.status_code >= 400:
                body = (response.text or "")[:500]
                logger.warning("LLM %s HTTP %s: %s", model_id, response.status_code, body)
                last_error = f"{model_id} HTTP {response.status_code}: {body or 'empty body'}"
                last_raw = _failed_generation_text(response) or body
                if not last_raw or not _is_retryable_validation_error(last_error):
                    continue
                content = last_raw
            else:
                try:
                    content = str(response.json()["choices"][0]["message"]["content"] or "")
                except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
                    last_error = _format_llm_error(model_id, error, timeout_s=timeout)
                    last_raw = (response.text or "")[:800]
                    continue
                last_raw = content

            recovered = False
            recovery_failed = False
            try:
                patch = _parse_and_normalize(content)
            except ValueError as error:
                from packages.agent.patch import QualityGateError

                if isinstance(error, QualityGateError) and error.category in _GATE_NO_RETRY:
                    raise
                if not _is_retryable_validation_error(error):
                    raise
                recovered = True
                retry_payload = dict(payload)
                retry_payload["max_tokens"] = min(MAX_COMPLETION_TOKENS, 1024)
                if local:
                    retry_payload["options"] = {
                        "num_ctx": OLLAMA_NUM_CTX,
                        "num_predict": min(MAX_COMPLETION_TOKENS, 1024),
                    }
                if isinstance(error, QualityGateError) and error.category == "syntax_error":
                    repair_prompt = _syntax_repair_user_message(
                        str(error),
                        [
                            {
                                "path": error.file or "",
                                "content": str(error.details.get("content") or last_raw),
                            }
                        ],
                    )
                else:
                    repair_prompt = _json_repair_user_message(str(error), last_raw)
                retry_payload["messages"] = [
                    payload["messages"][0],
                    {"role": "user", "content": repair_prompt},
                ]
                retry_started = time.perf_counter()
                repaired = await _post_completion(retry_payload)
                retry_latency = time.perf_counter() - retry_started
                if repaired.status_code >= 400:
                    body = (repaired.text or "")[:500]
                    recovery_failed = True
                    raise ValueError(f"validation retry HTTP {repaired.status_code}: {body or 'empty body'}")
                content = str(repaired.json()["choices"][0]["message"]["content"] or "")
                last_raw = content
                try:
                    patch = _parse_and_normalize(content)
                except ValueError:
                    recovery_failed = True
                    raise
            local_repair = bool(patch.pop("_local_repair", False))
            patch["summary"] = strip_llm_summary_prefix(str(patch["summary"]))
            patch["model"] = model_id
            patch["structured_recovery"] = recovered or local_repair
            patch["raw_structured_ok"] = not recovered and not local_repair
            patch["recovery_failed"] = recovery_failed
            patch["first_attempt_latency"] = first_attempt_latency
            patch["retry_latency"] = retry_latency
            return patch
        except httpx.TimeoutException as error:
            last_error = _format_llm_error(model_id, error, timeout_s=timeout)
            logger.warning("LLM generate with %s failed: %s", model_id, last_error)
            continue
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, httpx.HTTPError) as error:
            last_error = _format_llm_error(model_id, error, timeout_s=timeout)
            logger.warning("LLM generate with %s failed: %s", model_id, last_error)
            continue

    if is_health_request(request):
        return deterministic_patch(request, files)

    quality_gate = None
    if "QUALITY_GATE:" in last_error:
        quality_gate = {"message": last_error}
    raise PatchGenerationError(
        f"Patch generation failed across local models ({', '.join(candidates[:4])}…): {last_error}",
        raw_completion=_raw_preview(last_raw),
        quality_gate=quality_gate,
        first_attempt_latency=first_attempt_latency,
        retry_latency=retry_latency,
        raw_structured_ok=False,
        structured_recovery=False,
        recovery_failed=bool(retry_latency),
    )


def _raw_preview(text: str, limit: int = 800) -> str:
    blob = text or ""
    if len(blob) <= limit * 2:
        return blob
    return blob[:limit] + "\n…\n" + blob[-limit:]

