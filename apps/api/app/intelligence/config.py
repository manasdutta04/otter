"""Config, Docker, CI detection."""
from __future__ import annotations

from pathlib import Path


def detect_config(root: Path, files: list[Path]) -> tuple[list[str], list[str], list[str]]:
    config_files: list[str] = []
    ci: list[str] = []
    docker: list[str] = []
    config_names = {
        ".env.example",
        ".env.sample",
        "tsconfig.json",
        "jsconfig.json",
        "eslint.config.js",
        "eslint.config.mjs",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        "prettier.config.js",
        ".prettierrc",
        "components.json",
        "drizzle.config.ts",
        "drizzle.config.js",
        "tailwind.config.ts",
        "tailwind.config.js",
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "vite.config.ts",
        "vite.config.js",
    }
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        name = path.name.lower()
        if name in {n.lower() for n in config_names} or name.startswith(".env"):
            config_files.append(rel)
        if ".github/workflows" in rel.replace("\\", "/") or name in {"Jenkinsfile", ".gitlab-ci.yml"}:
            ci.append(rel)
        if name in {"dockerfile", "compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}:
            docker.append(rel)
        if rel.startswith("docker/") or "/docker/" in f"/{rel}/":
            if name.endswith((".yml", ".yaml", "dockerfile")) or name == "dockerfile":
                docker.append(rel)
    return sorted(set(config_files))[:40], sorted(set(ci))[:40], sorted(set(docker))[:40]
