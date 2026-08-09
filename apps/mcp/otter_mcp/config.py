from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OtterMcpConfig:
    api_url: str
    session: str
    repo_root: Path | None
    repository_id: str | None
    repository_data_dir: Path


def load_config() -> OtterMcpConfig:
    api_url = os.getenv("OTTER_API_URL", "").rstrip("/")
    session = os.getenv("OTTER_SESSION", "")
    repo_root_env = os.getenv("OTTER_REPO_ROOT", "").strip()
    repository_id = os.getenv("OTTER_REPOSITORY_ID", "").strip() or None
    data_dir = Path(os.getenv("REPOSITORY_DATA_DIR", "") or Path.home() / ".otter" / "repositories")

    config_path = Path.home() / ".otter" / "config.json"
    if config_path.is_file():
        try:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
            if not api_url:
                api_url = str(parsed.get("apiUrl") or "").rstrip("/")
            if not session:
                session = str(parsed.get("session") or "")
            if not repository_id:
                repository_id = str(parsed.get("activeRepoId") or "") or None
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    repo_root = Path(repo_root_env).resolve() if repo_root_env else None
    return OtterMcpConfig(
        api_url=api_url or "http://127.0.0.1:8000",
        session=session,
        repo_root=repo_root if repo_root and repo_root.is_dir() else None,
        repository_id=repository_id,
        repository_data_dir=data_dir,
    )
