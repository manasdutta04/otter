"""Authentication surface detection."""
from __future__ import annotations

from pathlib import Path

from .scanner import read_text_capped
from .types import AuthSignal

AUTH_PATH_HINTS = ("auth", "login", "session", "passport", "next-auth", "oauth", "credential", "middleware")


def detect_auth(root: Path, files: list[Path], dep_names: set[str]) -> list[AuthSignal]:
    signals: list[AuthSignal] = []
    auth_files: list[str] = []

    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        rel_l = rel.lower()
        if any(hint in rel_l for hint in AUTH_PATH_HINTS):
            auth_files.append(rel)
            continue
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".py"}:
            continue
        text = read_text_capped(path, 40_000).lower()
        if any(
            tok in text
            for tok in ("passport.", "next-auth", "bcrypt", "jsonwebtoken", "express-session", "getserversession")
        ):
            auth_files.append(rel)

    auth_files = sorted(set(auth_files))[:30]

    if "passport" in dep_names or "passport-local" in dep_names:
        signals.append(AuthSignal(mechanism="passport", files=auth_files, notes="Passport strategy detected in dependencies"))
    if "next-auth" in dep_names or "@auth/core" in dep_names:
        signals.append(AuthSignal(mechanism="next-auth", files=auth_files, notes="NextAuth / Auth.js dependency"))
    if "bcrypt" in dep_names or "bcryptjs" in dep_names or "argon2" in dep_names:
        signals.append(AuthSignal(mechanism="password-hashing", files=auth_files, notes="Password hashing library present"))
    if "jsonwebtoken" in dep_names or "jose" in dep_names:
        signals.append(AuthSignal(mechanism="jwt", files=auth_files, notes="JWT library present"))
    if "express-session" in dep_names:
        signals.append(AuthSignal(mechanism="session", files=auth_files, notes="express-session dependency"))
    if not signals and auth_files:
        signals.append(AuthSignal(mechanism="path-heuristic", files=auth_files, notes="Auth-related paths or tokens in source"))

    return signals
