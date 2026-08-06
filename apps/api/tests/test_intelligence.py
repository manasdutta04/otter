"""Phase 1 repository intelligence detector tests."""
from __future__ import annotations

from pathlib import Path

from app.intelligence import analyze_repository, analysis_to_legacy_dict


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_express_drizzle_fixture(tmp_path: Path):
    _write(
        tmp_path / "package.json",
        '{"name":"demo","dependencies":{"express":"^4.0.0","drizzle-orm":"^0.39.0","passport":"^0.7.0","bcryptjs":"^2.4.3"}}',
    )
    _write(
        tmp_path / "server/routes.ts",
        'import express from "express";\nconst app = express();\napp.post("/api/login", (_req, res) => res.json({ok:true}));\napp.get("/api/health", (_req, res) => res.json({ok:true}));\n',
    )
    _write(
        tmp_path / "shared/schema.ts",
        'import { pgTable, text } from "drizzle-orm/pg-core";\nexport const users = pgTable("users", { id: text("id"), email: text("email") });\n',
    )
    _write(tmp_path / "server/index.ts", 'import "./routes";\n')
    analysis = analyze_repository(tmp_path)
    assert "Express" in analysis.frameworks
    assert "Drizzle ORM" in analysis.frameworks
    assert any(r.path == "/api/login" for r in analysis.api_routes)
    assert any(db.orm == "drizzle" for db in analysis.databases)
    assert any(a.mechanism == "passport" for a in analysis.auth)
    legacy = analysis_to_legacy_dict(analysis)
    assert "analysis" in legacy
    assert isinstance(legacy["folders_rich"], list)


def test_fastapi_fixture(tmp_path: Path):
    _write(tmp_path / "requirements.txt", "fastapi==0.115.0\nuvicorn==0.34.0\nsqlalchemy==2.0.0\n")
    _write(
        tmp_path / "main.py",
        'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\nasync def health():\n    return {"ok": True}\n',
    )
    analysis = analyze_repository(tmp_path)
    assert "FastAPI" in analysis.frameworks or "Python" in analysis.languages
    assert any(r.path == "/health" and r.method == "GET" for r in analysis.api_routes)
    assert "pip" in analysis.package_managers
