"""API route detection — heuristics + light Python AST."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from .scanner import read_text_capped
from .types import ApiRoute

EXPRESS_ROUTE = re.compile(
    r"""(?:app|router)\.(get|post|put|patch|delete|use)\(\s*['"`]([^'"`]+)['"`]""",
    re.IGNORECASE,
)
FASTAPI_DECORATOR = re.compile(
    r"""@(?:app|router)\.(get|post|put|patch|delete)\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)


def detect_routes(root: Path, files: list[Path]) -> list[ApiRoute]:
    routes: list[ApiRoute] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        suffix = path.suffix.lower()
        if suffix in {".ts", ".tsx", ".js", ".jsx"}:
            routes.extend(_js_routes(path, rel))
            routes.extend(_next_app_routes(rel))
        elif suffix == ".py":
            routes.extend(_py_routes(path, rel))
        if len(routes) >= 80:
            break
    # Dedupe
    seen: set[tuple[str, str, str]] = set()
    unique: list[ApiRoute] = []
    for route in routes:
        key = (route.method.upper(), route.path, route.file)
        if key in seen:
            continue
        seen.add(key)
        unique.append(route)
    return unique[:80]


def _js_routes(path: Path, rel: str) -> list[ApiRoute]:
    content = read_text_capped(path)
    found: list[ApiRoute] = []
    for match in EXPRESS_ROUTE.finditer(content):
        method, route_path = match.group(1), match.group(2)
        if method.lower() == "use" and not route_path.startswith("/"):
            continue
        line = content[: match.start()].count("\n") + 1
        found.append(ApiRoute(method=method.upper() if method.lower() != "use" else "USE", path=route_path, file=rel, line=line))
    return found


def _next_app_routes(rel: str) -> list[ApiRoute]:
    # app/api/health/route.ts → /api/health
    lowered = rel.replace("\\", "/")
    match = re.match(r"^(?:src/)?app/(api(?:/[^/]+)*)/route\.(ts|js|tsx|jsx)$", lowered)
    if not match:
        return []
    path = "/" + match.group(1)
    return [ApiRoute(method="GET", path=path, file=rel, line=None)]



def _py_routes(path: Path, rel: str) -> list[ApiRoute]:
    content = read_text_capped(path)
    found: list[ApiRoute] = []
    for match in FASTAPI_DECORATOR.finditer(content):
        line = content[: match.start()].count("\n") + 1
        found.append(ApiRoute(method=match.group(1).upper(), path=match.group(2), file=rel, line=line))
    # AST for @app.get("/x") style if regex missed
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            route = _decorator_route(dec)
            if route:
                found.append(ApiRoute(method=route[0], path=route[1], file=rel, line=getattr(node, "lineno", None)))
    return found


def _decorator_route(dec: ast.AST) -> tuple[str, str] | None:
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    method = None
    if isinstance(func, ast.Attribute) and func.attr in {"get", "post", "put", "patch", "delete"}:
        method = func.attr.upper()
    if not method or not dec.args:
        return None
    arg0 = dec.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return method, arg0.value
    return None
