"""Hatch build hook: sync monorepo intelligence packages into the MCP wheel."""
from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

BUNDLE = (
    "impact",
    "architecture",
    "verify",
    "retrieval",
)


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "sync-bundled-packages"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        mono_packages = root.parents[1] / "packages"
        # When building from an sdist, bundled packages are already under ./packages
        dest = root / "packages"
        if not mono_packages.is_dir():
            if (dest / "impact").is_dir():
                return
            raise RuntimeError(
                "Cannot find monorepo packages/ or pre-bundled apps/mcp/packages/. "
                "Build otter-mcp from the Otter git checkout."
            )

        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        (dest / "__init__.py").write_text(
            '"""Bundled Otter engineering packages for otter-mcp."""\n',
            encoding="utf-8",
        )
        for name in BUNDLE:
            src = mono_packages / name
            if not src.is_dir():
                raise RuntimeError(f"Missing package directory: {src}")
            shutil.copytree(
                src,
                dest / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
            )
        planner_src = mono_packages / "planner" / "__init__.py"
        planner_dest = dest / "planner"
        planner_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(planner_src, planner_dest / "__init__.py")
