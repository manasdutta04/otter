"""LLM helpers for approval-gated coding tasks."""
from __future__ import annotations

import json
import logging
import re
import socket
from pathlib import Path

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

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
MAX_COMPLETION_TOKENS = 8192
# Prompt context caps for local 7B-class models (chars, not tokens).
CONTEXT_FILE_LIMIT = 6
CONTEXT_CHARS_PER_FILE = 3000
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
    "auth",
    "authentication",
    "login",
    "password",
    "signup",
    "signin",
    "sign-up",
    "sign-in",
    "register",
    "credential",
    "session",
    "oauth",
}
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
    words = set(re.findall(r"[a-z0-9_-]+", request.lower()))
    return bool(words & _AUTH_REQUEST_TERMS) or "email/password" in request.lower()


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
        users_table = bool(
            re.search(r"""pgTable\(\s*['"]users['"]""", joined)
            or re.search(r"""(?:export\s+)?const\s+users\s*=""", joined)
            or re.search(r"""class\s+User\b""", joined)
            or re.search(r"""__tablename__\s*=\s*['"]users['"]""", joined)
        )
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
        raise ValueError("Rejected low-quality patch: " + "; ".join(unique[:6]))


def _salvage_truncated_json(text: str) -> dict | None:
    """Recover whole `files[]` entries from a response cut off mid-generation.

    Groq returns the partial completion in `failed_generation`; everything before the
    truncation point is still a usable patch, so keep the complete entries.
    """
    decoder = json.JSONDecoder()
    summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    files_start = text.find("[", text.find('"files"')) if '"files"' in text else -1
    if files_start == -1:
        return None
    entries: list[dict[str, str]] = []
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
    if not entries:
        return None
    summary = summary_match.group(1) if summary_match else "Recovered partial patch"
    return {"summary": json.loads(f'"{summary}"'), "files": entries, "truncated": True}


def _extract_json_object(content: str) -> dict:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
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


def _normalize_patch(result: dict, *, originals: dict[str, str] | None = None, request: str = "") -> dict[str, object]:
    originals = originals or {}
    summary = strip_llm_summary_prefix(str(result.get("summary") or "").strip())
    files = result.get("files")
    if not summary or not isinstance(files, list) or not files:
        raise ValueError("Invalid patch shape")

    declared_deps: dict[str, str] = {}
    raw_deps = result.get("dependencies")
    if isinstance(raw_deps, dict):
        declared_deps.update({str(k): str(v) for k, v in raw_deps.items()})

    normalized_files: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip().replace("\\", "/")
        content = item.get("content")
        if not path or content is None:
            continue
        if Path(path).is_absolute() or ".." in Path(path).parts:
            continue
        lowered = path.lower()
        if lowered.startswith("otter_") or lowered in {"otter_health.py", "otter_change_request.md"}:
            continue
        if lowered in MANIFEST_PATHS:
            # Manifests are merged from the dependency delta, never rewritten wholesale.
            if lowered == "package.json":
                declared_deps.update(_package_dependency_delta(originals.get(path, ""), str(content)))
            continue
        normalized_files.append({"path": path, "content": str(content)})

    # Small local models often import bcryptjs/uuid without filling `dependencies`.
    declared_deps.update(_missing_npm_imports(normalized_files, originals, declared_deps))

    if declared_deps:
        base_manifest = originals.get("package.json") or '{"name":"app","dependencies":{}}'
        merged = _merge_dependencies(base_manifest, declared_deps)
        if merged is not None:
            normalized_files = [item for item in normalized_files if item["path"] != "package.json"]
            normalized_files.append({"path": "package.json", "content": merged})
        else:
            # Last resort: tell the validator these imports are intentional deps.
            originals = {
                **originals,
                "package.json": json.dumps(
                    {"dependencies": {**_package_names_as_deps(originals.get("package.json", "")), **declared_deps}},
                    indent=2,
                )
                + "\n",
            }

    if not normalized_files:
        raise ValueError("Patch contained no usable files")
    validate_patch_quality(request, normalized_files, originals)
    return {"summary": summary, "files": normalized_files, "source": "llm"}


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
) -> dict[str, object]:
    """Generate a real patch via LLM, or a deterministic health patch. Never TODO stubs."""
    originals = {item["path"]: item["content"] for item in files}
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
    context = "\n\n".join(
        f"FILE: {item['path']}\n{item['content'][:CONTEXT_CHARS_PER_FILE]}" for item in limited
    )
    plan_block = ""
    if plan_context:
        steps = (plan_context.get("steps") or [])[:5]
        affected = (plan_context.get("affected_files") or [])[:8]
        plan_block = (
            "\n\nImplementation plan hints (use as guidance, not as a TODO list):\n"
            f"Title: {plan_context.get('title', '')}\n"
            f"Summary: {str(plan_context.get('summary') or '')[:400]}\n"
            f"Steps: {json.dumps(steps)}\n"
            f"Affected files: {json.dumps(affected)}\n"
        )

    auth_rules = ""
    if _is_auth_request(request):
        auth_rules = (
            "\nAuth-specific rules (mandatory):\n"
            "A. Add a real `users` (or equivalent) table/model with email + password hash columns — "
            "never reuse domain tables like `cards` for credentials.\n"
            "B. Implement register + login routes that bcrypt/argon2 hash and verify passwords.\n"
            "C. If using sessions, add express-session (or passport/next-auth) and wire middleware — "
            "do not assign `req.session` without that dependency.\n"
            "D. No stub comments ('Replace with actual…', TODO placeholders).\n"
            "E. Use real Drizzle APIs for this stack (no `.select().get()` on node-postgres drizzle).\n"
        )
    prompt = (
        "Return ONLY valid JSON (no markdown fences) with this shape:\n"
        '{"summary":"short description",'
        '"dependencies":{"package-name":"^1.2.3"},'
        '"files":[{"path":"relative/path.ext","content":"full file contents"}]}\n\n'
        "Rules:\n"
        "1. Implement the requested change for real — working code, not placeholders.\n"
        "2. NEVER add TODO(Otter), FIXME stubs, or 'implement later' comments as the change.\n"
        "3. Prefer editing existing auth/route/entrypoint files that match the stack.\n"
        "4. Never create otter_*.py, OTTER_*.md, or disconnected stub files.\n"
        "5. If a /health (or equivalent) already exists, do not duplicate it.\n"
        "6. Match existing style, imports, and framework conventions EXACTLY.\n"
        "7. Change as few files as possible, but include every file required for a working change.\n"
        "8. Return FULL file contents for each changed path.\n"
        "9. NEVER invent APIs (no fake drizzle helpers, no made-up packages).\n"
        "10. If the repo uses drizzle-orm/pg-core + node-postgres, keep that pattern; extend pgTable schemas.\n"
        "11. For auth/password: hash passwords (bcrypt/argon2/scrypt); never store plaintext.\n"
        "12. NEVER output package.json or lock files. Declare new packages in `dependencies` instead — "
        "they are merged into package.json automatically.\n"
        "13. List the most important file first; the response is length-capped.\n"
        "14. Summary must be plain English for humans — never include model names or `[llm:…]` tags.\n"
        f"{auth_rules}"
        f"Requested change: {request}\n"
        f"{plan_block}\n"
        f"Repository context:\n{context}"
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
    local = _is_ollama_base(base)
    timeout = 300.0 if local else 120.0
    request_base = _resolve_base_url(base)

    for model_id in candidates:
        payload: dict[str, object] = {
            "model": model_id,
            "temperature": 0,
            "max_tokens": MAX_COMPLETION_TOKENS,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cautious senior software engineer. "
                        "Return only compact JSON with keys summary, dependencies and files. "
                        "Never wrap JSON in markdown. "
                        "Produce a real implementation that compiles against the existing stack. "
                        "Never invent ORM APIs. Never store plaintext passwords. Never TODO-only patches. "
                        "For email/password auth: add a users schema, hash passwords, and real session/auth wiring. "
                        "Summary text must not mention model names."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        if not local:
            payload["max_completion_tokens"] = MAX_COMPLETION_TOKENS
        else:
            # Shrink KV cache so local 7B models can load on low-RAM hosts.
            payload["options"] = {"num_ctx": OLLAMA_NUM_CTX, "num_predict": MAX_COMPLETION_TOKENS}
        if _supports_json_object(base):
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{request_base.rstrip('/')}/chat/completions",
                    headers=_llm_headers(key, base),
                    json=payload,
                )
            if response.status_code >= 400:
                body = (response.text or "")[:500]
                logger.warning("LLM %s HTTP %s: %s", model_id, response.status_code, body)
                last_error = f"{model_id} HTTP {response.status_code}: {body}"
                partial = _failed_generation_text(response)
                if not partial:
                    continue
                try:
                    patch = _normalize_patch(
                        _extract_json_object(partial), originals=originals, request=request
                    )
                except ValueError as error:
                    last_error = f"{model_id} truncated: {error}"
                    logger.warning("LLM %s truncated and unsalvageable: %s", model_id, error)
                    continue
                patch["summary"] = strip_llm_summary_prefix(str(patch["summary"]))
                patch["model"] = model_id
                return patch
            content = response.json()["choices"][0]["message"]["content"]
            patch = _normalize_patch(_extract_json_object(content), originals=originals, request=request)
            patch["summary"] = strip_llm_summary_prefix(str(patch["summary"]))
            patch["model"] = model_id
            return patch
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, httpx.HTTPError) as error:
            last_error = f"{model_id}: {error}"
            logger.warning("LLM generate with %s failed: %s", model_id, error)
            continue

    # Health-only escape hatch after LLM failure
    if is_health_request(request):
        return deterministic_patch(request, files)

    raise PatchGenerationError(
        f"Patch generation failed across local models ({', '.join(candidates[:4])}…): {last_error}"
    )
