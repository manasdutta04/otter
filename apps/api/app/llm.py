"""LLM helpers for approval-gated coding tasks."""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from .config import get_settings

HEALTH_PATTERNS = (
    re.compile(r"[\"']/health[\"']"),
    re.compile(r"@app\.get\(\s*[\"']/health"),
    re.compile(r"router\.(get|Get)\(\s*[\"']/health"),
    re.compile(r"export\s+async\s+function\s+GET"),
)


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
    if not match:
        raise ValueError("No JSON object found in model response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Model JSON was not an object")
    return data


def _normalize_patch(result: dict) -> dict[str, object]:
    summary = str(result.get("summary") or "").strip()
    files = result.get("files")
    if not summary or not isinstance(files, list) or not files:
        raise ValueError("Invalid patch shape")
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
        # Reject throwaway stub/note files from model output
        lowered = path.lower()
        if lowered.startswith("otter_") or lowered in {"otter_health.py", "otter_change_request.md"}:
            continue
        normalized_files.append({"path": path, "content": str(content)})
    if not normalized_files:
        raise ValueError("Patch contained no usable files")
    return {"summary": summary, "files": normalized_files}


def _score_file(path: str, request: str) -> float:
    words = set(re.findall(r"[a-z0-9_]+", request.lower()))
    lowered = path.lower()
    score = 0.0
    for word in words:
        if len(word) > 2 and word in lowered:
            score += 3.0
    basename = Path(lowered).name
    if basename in {"main.py", "app.py", "server.py", "index.ts", "index.js", "server.ts", "server.js", "route.ts", "routes.ts", "app.ts", "app.js"}:
        score += 4.0
    if "health" in words and "health" in lowered:
        score += 10.0
    if any(part in lowered for part in ("/api/", "routes/", "router", "controllers/")):
        score += 2.0
    if lowered.endswith((".md", ".json", ".lock")):
        score -= 5.0
    return score


def _pick_targets(files: list[dict[str, str]], request: str, *, limit: int = 5) -> list[dict[str, str]]:
    ranked = sorted((( _score_file(item["path"], request), item) for item in files), key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked if score > 0][:limit] or files[:limit]


def _find_existing_health(files: list[dict[str, str]]) -> dict[str, str] | None:
    for item in files:
        content = item["content"]
        path = item["path"].lower()
        if "health" in path and path.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".go")):
            return item
        if any(pattern.search(content) for pattern in HEALTH_PATTERNS):
            return item
        if re.search(r"\bhealth\b", content, re.I) and ("endpoint" in content.lower() or "route" in content.lower() or "@app.get" in content or "router." in content):
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
                f"A health surface already exists in `{existing['path']}`. "
                "No duplicate route was added to avoid conflicts. Review that file before changing behavior."
            ),
            "files": [{
                "path": existing["path"],
                "content": existing["content"],
            }],
            "noop": True,
        }

    if stack == "next":
        # App Router preferred when app/ exists
        has_app_dir = any(item["path"].startswith("app/") for item in files)
        if has_app_dir or not any(item["path"].startswith("pages/") for item in files):
            path = "app/api/health/route.ts"
            content = (
                "import { NextResponse } from \"next/server\";\n\n"
                "export async function GET() {\n"
                "  return NextResponse.json({ status: \"ok\" });\n"
                "}\n"
            )
            return {
                "summary": "Adds a Next.js App Router health endpoint at `app/api/health/route.ts`.",
                "files": [{"path": path, "content": content}],
            }
        path = "pages/api/health.ts"
        content = (
            "import type { NextApiRequest, NextApiResponse } from \"next\";\n\n"
            "export default function handler(_req: NextApiRequest, res: NextApiResponse) {\n"
            "  res.status(200).json({ status: \"ok\" });\n"
            "}\n"
        )
        return {
            "summary": "Adds a Next.js Pages Router health endpoint at `pages/api/health.ts`.",
            "files": [{"path": path, "content": content}],
        }

    if stack == "fastapi":
        targets = _pick_targets(files, "fastapi main app route health")
        target = next((item for item in targets if item["path"].endswith(".py")), None)
        if target and ("FastAPI" in target["content"] or "@app." in target["content"]):
            if "/health" in target["content"]:
                return {
                    "summary": f"`{target['path']}` already references health; left unchanged to avoid duplicate routes.",
                    "files": [{"path": target["path"], "content": target["content"]}],
                    "noop": True,
                }
            addition = (
                "\n\n@app.get(\"/health\")\n"
                "async def health() -> dict[str, str]:\n"
                "    return {\"status\": \"ok\"}\n"
            )
            return {
                "summary": f"Adds a FastAPI `/health` route to `{target['path']}` using the existing app instance.",
                "files": [{"path": target["path"], "content": target["content"].rstrip() + addition + "\n"}],
            }

    if stack in {"node", "node_or_flask"}:
        targets = _pick_targets(files, request + " server index app routes")
        target = next((item for item in targets if item["path"].endswith((".ts", ".js"))), None)
        if target:
            content = target["content"]
            if "/health" in content:
                return {
                    "summary": f"`{target['path']}` already exposes health; left unchanged to avoid conflicts.",
                    "files": [{"path": target["path"], "content": content}],
                    "noop": True,
                }
            if "express" in content.lower() or "app.get" in content or "router.get" in content:
                addition = (
                    "\n\napp.get(\"/health\", (_req, res) => {\n"
                    "  res.status(200).json({ status: \"ok\" });\n"
                    "});\n"
                )
                return {
                    "summary": f"Adds an Express-style `/health` route to `{target['path']}`.",
                    "files": [{"path": target["path"], "content": content.rstrip() + addition + "\n"}],
                }

    # Last resort: conventional API route path for JS repos, route module for Python — never otter_*.py
    if any(item["path"].endswith((".ts", ".tsx", ".js", ".jsx")) for item in files):
        path = "app/api/health/route.ts"
        content = (
            "import { NextResponse } from \"next/server\";\n\n"
            "export async function GET() {\n"
            "  return NextResponse.json({ status: \"ok\" });\n"
            "}\n"
        )
        return {
            "summary": "Adds `app/api/health/route.ts` following common Next.js API conventions.",
            "files": [{"path": path, "content": content}],
        }
    path = "api/health.py"
    content = (
        "\"\"\"Health route module — wire into your app router if not auto-discovered.\"\"\"\n\n"
        "def health() -> dict[str, str]:\n"
        "    return {\"status\": \"ok\"}\n"
    )
    return {
        "summary": "Adds `api/health.py` as a conventional health module for review and wiring.",
        "files": [{"path": path, "content": content}],
    }


def deterministic_patch(request: str, files: list[dict[str, str]]) -> dict[str, object]:
    """Framework-aware fallback patch that avoids duplicate routes and orphan stubs."""
    lowered = request.lower()
    stack = _detect_stack(files)
    if "health" in lowered and any(term in lowered for term in ("endpoint", "route", "api", "/health", "healthcheck")):
        return _health_patch_for_stack(stack, files, request)

    targets = _pick_targets(files, request)
    if not targets:
        raise ValueError("No suitable source files found to attach this change")

    target = targets[0]
    marker = f"TODO(Otter): {request.strip()}"
    if marker in target["content"]:
        return {
            "summary": f"`{target['path']}` already contains this Otter TODO; left unchanged to avoid duplicate markers.",
            "files": [{"path": target["path"], "content": target["content"]}],
            "noop": True,
        }
    comment = "# " if target["path"].endswith(".py") else "// "
    addition = f"\n\n{comment}{marker}\n{comment}Implement carefully and remove this marker when done.\n"
    return {
        "summary": f"Adds an implementation TODO in `{target['path']}` for: {request.strip()}",
        "files": [{"path": target["path"], "content": target["content"].rstrip() + addition + "\n"}],
    }


async def generate_patch(request: str, files: list[dict[str, str]]) -> dict[str, object]:
    settings = get_settings()
    if not settings.llm_api_key:
        return deterministic_patch(request, files)

    context = "\n\n".join(f"FILE: {item['path']}\n{item['content'][:8000]}" for item in files[:15])
    prompt = (
        "Return ONLY valid JSON (no markdown fences) with this shape:\n"
        '{"summary":"short description","files":[{"path":"relative/path.ext","content":"full file contents"}]}\n\n'
        "Rules:\n"
        "1. Prefer editing an existing route/entrypoint that matches the stack.\n"
        "2. Never create otter_*.py, OTTER_*.md, or disconnected stub files.\n"
        "3. If a /health (or equivalent) already exists, do not duplicate it — return the existing file unchanged and explain in summary.\n"
        "4. Match existing style, imports, and framework conventions (Next.js, FastAPI, Express, etc.).\n"
        "5. Change as few files as possible.\n"
        f"Requested change: {request}\n\nRepository context:\n{context}"
    )
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cautious senior software engineer. "
                    "Return only compact JSON with keys summary and files. "
                    "Never wrap JSON in markdown. Avoid duplicate endpoints and orphan stubs."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    if "openai.com" in settings.llm_base_url or settings.llm_model.startswith("gpt-"):
        payload["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
        if response.status_code >= 400:
            return deterministic_patch(request, files)
        content = response.json()["choices"][0]["message"]["content"]
        return _normalize_patch(_extract_json_object(content))
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, httpx.HTTPError):
        return deterministic_patch(request, files)
