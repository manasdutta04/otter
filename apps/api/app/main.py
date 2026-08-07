import sys
from pathlib import Path

# Add project root to sys.path so packages modules load cleanly
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode
import json
import os
import re
import shutil
import subprocess
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from git import GitCommandError, Repo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import (
    AuthSession, CodeChangeTask, GeneratedDocument, MemoryEntry, Repository,
    RepositoryArchitectureAnalysis, RepositoryGraph, RepositoryHealth,
    RepositoryImportJob, RepositoryIntelligence, RepositoryPerformance,
    RepositoryPlan, RepositoryReview, User
)
from packages.retrieval import answer_repository_question
from app.knowledge import add_memory, generate_overview
from app.llm import (
    CONTEXT_CHARS_PER_FILE,
    CONTEXT_FILE_LIMIT,
    PatchGenerationError,
    generate_patch,
    is_todo_only_patch,
    strip_llm_summary_prefix,
    validate_patch_quality,
)
from app.planner import build_plan, save_plan
from app.schemas import (
    ArchitectureAnalysisResponse, ArchitectureGraphResponse, AuthIntelligence,
    ApiRouteIntelligence, ChatRequest, ChatResponse, CodeTaskCreate, CodeTaskDecision,
    CodeTaskResponse, DatabaseIntelligence, DocumentResponse, FolderIntelligence,
    HealthResponse, HealthResponseReport, ImportStatus, IntelligenceAnalysis,
    IntelligenceResponse, LlmModelsResponse, LlmSettingsResponse, LlmSettingsUpdate,
    LlmTestResponse, MemoryCreate, MemoryResponse, PatchProposal,
    PerformanceResponse, PlanRequest, PlanResponse, PullRequestRequest,
    PullRequestResponse, RepositoryCreate, RepositoryListResponse,
    RepositorySummary, ReviewResponse, TestResponse
)
from app.store import RepositoryStore
from app.worker import enqueue_import, import_repository_task


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
_cors_origins = {
    settings.next_public_url.rstrip("/"),
    "http://127.0.0.1:3000",
    "http://localhost:3000",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = RepositoryStore()


def normalize_complexity(value: str) -> str:
    lowered = (value or "medium").strip().lower()
    return lowered if lowered in {"low", "medium", "high"} else "medium"


def serialize_plan(plan: RepositoryPlan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        repository_id=plan.repository_id,
        request=plan.request,
        title=plan.title,
        complexity=normalize_complexity(plan.complexity),  # type: ignore[arg-type]
        summary=plan.summary,
        steps=json.loads(plan.steps),
        affected_files=json.loads(plan.affected_files),
        dependencies=json.loads(plan.dependencies),
        risks=json.loads(plan.risks),
        created_at=plan.created_at,
    )


def github_push_url(remote_url: str, token: str) -> str:
    """Build an HTTPS remote URL authenticated with the user OAuth token."""
    cleaned = remote_url.strip()
    if cleaned.startswith("git@github.com:"):
        path = cleaned.removeprefix("git@github.com:").removesuffix(".git")
        return f"https://x-access-token:{token}@github.com/{path}.git"
    if "github.com/" in cleaned:
        path = cleaned.split("github.com/", 1)[1].removesuffix(".git")
        return f"https://x-access-token:{token}@github.com/{path}.git"
    raise HTTPException(status_code=422, detail="Only GitHub remotes are supported for pull requests")


def _package_has_test_script(package_json: Path) -> bool:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return isinstance(scripts, dict) and bool(scripts.get("test"))


def run_repository_tests(root: Path) -> TestResponse:
    package_json = root / "package.json"
    if package_json.exists():
        npm = shutil.which("npm")
        if not npm:
            return TestResponse(
                passed=False,
                output=(
                    "This repository looks like a Node project, but `npm` is not available inside the Otter API container. "
                    "Rebuild the API image (Node 20 is required) or run tests locally / via CI."
                ),
            )
        install_log = ""
        try:
            # Prefer reproducible install when a lockfile exists.
            lockfile = root / "package-lock.json"
            install_cmd = [npm, "ci"] if lockfile.exists() else [npm, "install", "--no-audit", "--no-fund"]
            install = subprocess.run(
                install_cmd,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=240,
            )
            install_log = (install.stdout + "\n" + install.stderr)[-6000:]
            if install.returncode != 0:
                # Fall back to npm install if ci fails (common on partial clones).
                if install_cmd[1] == "ci":
                    install = subprocess.run(
                        [npm, "install", "--no-audit", "--no-fund"],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=240,
                    )
                    install_log = (install.stdout + "\n" + install.stderr)[-6000:]
                if install.returncode != 0:
                    return TestResponse(
                        passed=False,
                        output=f"npm install failed:\n{install_log}",
                    )
            if not _package_has_test_script(package_json):
                return TestResponse(
                    passed=False,
                    output=(
                        "Dependencies installed, but package.json has no `test` script. "
                        "Add a test script or rely on CI for verification.\n"
                        f"{install_log[-2000:]}"
                    ),
                )
            result = subprocess.run(
                [npm, "test", "--", "--watchAll=false"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
                env={**os.environ, "CI": "true"},
            )
            output = (result.stdout + "\n" + result.stderr)[-12000:]
            return TestResponse(passed=result.returncode == 0, output=output or "npm test finished with no output")
        except (OSError, subprocess.TimeoutExpired) as error:
            return TestResponse(passed=False, output=f"npm test could not run: {error}\n{install_log}")
    try:
        probe = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if probe.returncode != 0:
            return TestResponse(
                passed=False,
                output="No test runner detected (no package.json test script / pytest unavailable). Use local tests or CI.",
            )
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + "\n" + result.stderr)[-12000:]
        return TestResponse(passed=result.returncode == 0, output=output)
    except (OSError, subprocess.TimeoutExpired) as error:
        return TestResponse(passed=False, output=str(error))

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


@app.get("/settings/llm", response_model=LlmSettingsResponse)
async def get_llm_settings(db: AsyncSession = Depends(get_db)) -> LlmSettingsResponse:
    from app.llm_settings import get_runtime

    runtime = await get_runtime(db)
    return LlmSettingsResponse(**runtime.to_public_dict())


@app.put("/settings/llm", response_model=LlmSettingsResponse)
async def put_llm_settings(payload: LlmSettingsUpdate, db: AsyncSession = Depends(get_db)) -> LlmSettingsResponse:
    from app.llm_settings import save_runtime

    if payload.provider == "ollama":
        base = payload.base_url.strip() or "http://host.docker.internal:11434/v1"
    else:
        base = payload.base_url.strip()
    runtime = await save_runtime(
        db,
        provider=payload.provider,
        base_url=base,
        model=payload.model,
        api_key=payload.api_key,
        free_failover=payload.free_failover,
        keep_existing_key=payload.keep_existing_key,
    )
    return LlmSettingsResponse(**runtime.to_public_dict())


@app.get("/settings/llm/models", response_model=LlmModelsResponse)
async def list_llm_models(db: AsyncSession = Depends(get_db)) -> LlmModelsResponse:
    from app.llm_settings import get_runtime, list_models

    runtime = await get_runtime(db)
    models = await list_models(runtime)
    return LlmModelsResponse(models=models, provider=runtime.provider, base_url=runtime.base_url)


@app.post("/settings/llm/test", response_model=LlmTestResponse)
async def test_llm_settings(db: AsyncSession = Depends(get_db)) -> LlmTestResponse:
    from app.llm_settings import get_runtime, test_runtime

    runtime = await get_runtime(db)
    result = await test_runtime(runtime)
    return LlmTestResponse(**result)

@app.get("/auth/github/login")
async def github_login(cli_port: int | None = None) -> RedirectResponse:
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    params: dict[str, str] = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user repo",
    }
    if cli_port is not None:
        if cli_port < 1024 or cli_port > 65535:
            raise HTTPException(status_code=422, detail="Invalid CLI callback port")
        params["state"] = f"cli:{cli_port}"
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{urlencode(params)}")

@app.get("/auth/github/callback")
async def github_callback(code: str, state: str | None = None, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    async with httpx.AsyncClient() as client:
        response = await client.post("https://github.com/login/oauth/access_token", data={"client_id": settings.github_client_id, "client_secret": settings.github_client_secret, "code": code}, headers={"Accept": "application/json"})
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise HTTPException(status_code=400, detail="GitHub did not return an access token")
        profile = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        profile.raise_for_status()
    github_user = profile.json()
    user = await db.scalar(select(User).where(User.github_id == str(github_user["id"])))
    if not user:
        user = User(
            id=token_urlsafe(16),
            github_id=str(github_user["id"]),
            login=github_user["login"],
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)
        await db.flush()  # ensure users row exists before auth_sessions FK insert
    else:
        user.login = github_user["login"]
        user.avatar_url = github_user.get("avatar_url")
    session_id = token_urlsafe(32)
    db.add(
        AuthSession(
            id=session_id,
            user_id=user.id,
            github_token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    await db.commit()
    if state and state.startswith("cli:"):
        try:
            port = int(state.split(":", 1)[1])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid CLI state") from exc
        return RedirectResponse(f"http://127.0.0.1:{port}/callback?session={session_id}")
    redirect = RedirectResponse(f"{settings.next_public_url.rstrip('/')}/app")
    redirect.set_cookie("otter_session", session_id, httponly=True, samesite="lax", secure=False, max_age=86400)
    return redirect

async def current_session(request: Request, db: AsyncSession = Depends(get_db)) -> AuthSession:
    session_id = request.cookies.get("otter_session") or request.headers.get("x-otter-session")
    session = await db.get(AuthSession, session_id or "")
    if not session or session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    return session

@app.get("/auth/me")
async def auth_me(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    try:
        session = await current_session(request, db)
        user = await db.get(User, session.user_id)
        return {"authenticated": True, "login": user.login if user else None}
    except HTTPException:
        return {"authenticated": False, "login": None}

@app.post("/auth/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    session_id = request.cookies.get("otter_session") or request.headers.get("x-otter-session")
    if session_id:
        session = await db.get(AuthSession, session_id)
        if session:
            await db.delete(session)
            await db.commit()
    response = Response(status_code=204)
    response.delete_cookie("otter_session")
    return response

@app.get("/repositories", response_model=RepositoryListResponse)
async def repositories(session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositoryListResponse:
    records = await store.list(db, session.user_id)
    return RepositoryListResponse(repositories=[RepositorySummary.model_validate(record, from_attributes=True) for record in records])

@app.post("/repositories", response_model=RepositorySummary, status_code=202)
async def import_repository(payload: RepositoryCreate, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositorySummary:
    if "github.com/" not in payload.url.lower():
        raise HTTPException(status_code=422, detail="Only GitHub repository URLs are supported")
    record, job = await store.create(db, session.user_id, payload.url)
    enqueue_import(job.id, record.id)
    return RepositorySummary.model_validate(record, from_attributes=True)

@app.get("/repositories/{repository_id}", response_model=RepositorySummary)
async def repository(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositorySummary:
    record = await store.get(db, session.user_id, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositorySummary.model_validate(record, from_attributes=True)

@app.get("/repositories/{repository_id}/intelligence", response_model=IntelligenceResponse)
async def intelligence(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> IntelligenceResponse:
    repository = await store.get(db, session.user_id, repository_id)
    record = await db.get(RepositoryIntelligence, repository_id)
    if not repository or not record:
        raise HTTPException(status_code=404, detail="Repository intelligence is not ready")
    return _serialize_intelligence(repository_id, record)


def _serialize_intelligence(repository_id: str, record: RepositoryIntelligence) -> IntelligenceResponse:
    raw_folders = json.loads(record.folders or "[]")
    folders: list = []
    for item in raw_folders:
        if isinstance(item, dict) and "path" in item:
            folders.append(
                FolderIntelligence(
                    path=str(item["path"]),
                    role=str(item.get("role") or "source"),
                    file_count=int(item.get("file_count") or 0),
                    explanation=(item.get("explanation") or None),
                )
            )
        else:
            folders.append(str(item))
    analysis = None
    try:
        blob = json.loads(getattr(record, "analysis_json", None) or "{}")
        if isinstance(blob, dict) and blob:
            # Attach folder explanations onto folder objects when present
            explanations = blob.get("folder_explanations") or {}
            if isinstance(explanations, dict):
                for folder in folders:
                    if isinstance(folder, FolderIntelligence) and folder.path in explanations:
                        folder.explanation = str(explanations[folder.path])
            def _route(r: dict) -> ApiRouteIntelligence | None:
                try:
                    return ApiRouteIntelligence(
                        method=str(r.get("method") or "GET"),
                        path=str(r.get("path") or ""),
                        file=str(r.get("file") or ""),
                        line=r.get("line"),
                    )
                except (TypeError, ValueError):
                    return None

            def _db(r: dict) -> DatabaseIntelligence | None:
                try:
                    return DatabaseIntelligence(
                        orm=str(r.get("orm") or ""),
                        evidence=str(r.get("evidence") or ""),
                        files=[str(x) for x in (r.get("files") or [])],
                    )
                except (TypeError, ValueError):
                    return None

            def _auth(r: dict) -> AuthIntelligence | None:
                try:
                    return AuthIntelligence(
                        mechanism=str(r.get("mechanism") or ""),
                        files=[str(x) for x in (r.get("files") or [])],
                        notes=str(r.get("notes") or ""),
                    )
                except (TypeError, ValueError):
                    return None

            analysis = IntelligenceAnalysis(
                summary_facts=list(blob.get("summary_facts") or []),
                languages=list(blob.get("languages") or []),
                package_managers=list(blob.get("package_managers") or []),
                frameworks=list(blob.get("frameworks") or []),
                api_routes=[m for r in (blob.get("api_routes") or []) if isinstance(r, dict) for m in [_route(r)] if m],
                databases=[m for r in (blob.get("databases") or []) if isinstance(r, dict) for m in [_db(r)] if m],
                auth=[m for r in (blob.get("auth") or []) if isinstance(r, dict) for m in [_auth(r)] if m],
                config_files=list(blob.get("config_files") or []),
                ci=list(blob.get("ci") or []),
                docker=list(blob.get("docker") or []),
                testing=list(blob.get("testing") or []),
                folder_explanations={str(k): str(v) for k, v in explanations.items()} if isinstance(explanations, dict) else {},
            )
    except (TypeError, ValueError, json.JSONDecodeError):
        analysis = None
    return IntelligenceResponse(
        repository_id=repository_id,
        summary=record.summary,
        tech_stack=json.loads(record.tech_stack or "[]"),
        folders=folders,
        entry_points=json.loads(record.entry_points or "[]"),
        architecture_signals=json.loads(record.architecture_signals or "[]"),
        analysis=analysis,
        analyzed_at=record.analyzed_at,
    )

@app.post("/repositories/{repository_id}/chat", response_model=ChatResponse)
async def repository_chat(repository_id: str, payload: ChatRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ChatResponse:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must finish importing before chat is available")
    root = Path(settings.repository_data_dir) / repository_id
    intel = await db.get(RepositoryIntelligence, repository_id)
    from app.intelligence.explain import explain_analysis, is_meta_architecture_question

    if intel and is_meta_architecture_question(payload.question):
        try:
            analysis = json.loads(getattr(intel, "analysis_json", None) or "{}")
            if isinstance(analysis, dict) and analysis:
                explanation = await explain_analysis(analysis, question=payload.question)
                parts = [explanation["summary"]]
                if explanation.get("auth_explanation"):
                    parts.append("Auth: " + explanation["auth_explanation"])
                if explanation.get("api_explanation"):
                    parts.append("API: " + explanation["api_explanation"])
                if explanation.get("folder_explanations"):
                    folder_bits = ", ".join(f"{k}: {v}" for k, v in list(explanation["folder_explanations"].items())[:8])
                    parts.append("Folders: " + folder_bits)
                return ChatResponse(answer="\n\n".join(parts), sources=["repository intelligence"], primary_file=None, primary_lines=None, excerpt=None)
        except Exception:  # noqa: BLE001 — fall through to retrieval
            pass
    result = answer_repository_question(root, payload.question)
    sources = [str(item["path"]) for item in result.get("sources", [])]
    return ChatResponse(
        answer=str(result["answer"]),
        sources=sources,
        primary_file=result.get("primary_file"),
        primary_lines=result.get("primary_lines"),
        excerpt=result.get("excerpt"),
    )

@app.post("/repositories/{repository_id}/plans", response_model=PlanResponse, status_code=201)
async def create_plan(repository_id: str, payload: PlanRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> PlanResponse:
    repository = await store.get(db, session.user_id, repository_id)
    intelligence_record = await db.get(RepositoryIntelligence, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must finish importing before planning is available")
    intelligence = {"entry_points": json.loads(intelligence_record.entry_points)} if intelligence_record else None
    plan = await save_plan(db, repository_id, session.user_id, payload.request, build_plan(Path(settings.repository_data_dir) / repository_id, payload.request, intelligence))
    return serialize_plan(plan)

@app.get("/repositories/{repository_id}/plans", response_model=list[PlanResponse])
async def list_plans(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    records = await db.scalars(select(RepositoryPlan).where(RepositoryPlan.repository_id == repository_id, RepositoryPlan.user_id == session.user_id).order_by(RepositoryPlan.created_at.desc()))
    return [serialize_plan(plan) for plan in records]

@app.get("/repositories/{repository_id}/architecture", response_model=ArchitectureGraphResponse)
async def architecture(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ArchitectureGraphResponse:
    repository = await store.get(db, session.user_id, repository_id)
    graph = await db.get(RepositoryGraph, repository_id)
    if not repository or not graph:
        raise HTTPException(status_code=404, detail="Architecture graph is not ready")
    return ArchitectureGraphResponse(repository_id=repository_id, nodes=json.loads(graph.nodes), edges=json.loads(graph.edges), generated_at=graph.generated_at)

@app.post("/repositories/{repository_id}/memory", response_model=MemoryResponse, status_code=201)
async def create_memory(repository_id: str, payload: MemoryCreate, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> MemoryResponse:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    entry = await add_memory(db, repository_id, session.user_id, payload.kind, payload.title, payload.content)
    return MemoryResponse.model_validate(entry, from_attributes=True)

@app.get("/repositories/{repository_id}/memory", response_model=list[MemoryResponse])
async def list_memory(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[MemoryResponse]:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    entries = await db.scalars(select(MemoryEntry).where(MemoryEntry.repository_id == repository_id, MemoryEntry.user_id == session.user_id).order_by(MemoryEntry.created_at.desc()))
    return [MemoryResponse.model_validate(entry, from_attributes=True) for entry in entries]

@app.post("/repositories/{repository_id}/documents/overview", response_model=DocumentResponse, status_code=201)
async def create_overview(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> DocumentResponse:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must be ready before documentation is generated")
    document = await generate_overview(db, repository_id, session.user_id, repository.name)
    return DocumentResponse.model_validate(document, from_attributes=True)

@app.get("/repositories/{repository_id}/documents", response_model=list[DocumentResponse])
async def list_documents(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[DocumentResponse]:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    documents = await db.scalars(select(GeneratedDocument).where(GeneratedDocument.repository_id == repository_id, GeneratedDocument.user_id == session.user_id).order_by(GeneratedDocument.created_at.desc()))
    return [DocumentResponse.model_validate(document, from_attributes=True) for document in documents]

@app.post("/repositories/{repository_id}/code-tasks", response_model=CodeTaskResponse, status_code=201)
async def create_code_task(repository_id: str, payload: CodeTaskCreate, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must be ready before creating a coding task")
    if payload.plan_id and not await db.scalar(select(RepositoryPlan).where(RepositoryPlan.id == payload.plan_id, RepositoryPlan.repository_id == repository_id, RepositoryPlan.user_id == session.user_id)):
        raise HTTPException(status_code=404, detail="Plan not found")
    open_statuses = ("draft", "ready_for_approval", "patch_ready", "approved")
    duplicate = await db.scalar(
        select(CodeChangeTask).where(
            CodeChangeTask.repository_id == repository_id,
            CodeChangeTask.user_id == session.user_id,
            CodeChangeTask.request == payload.request,
            CodeChangeTask.status.in_(open_statuses),
        ).order_by(CodeChangeTask.created_at.desc())
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"An open task for this request already exists ({duplicate.id}, status={duplicate.status}). Reject or finish it before creating another.",
        )
    task = CodeChangeTask(
        id=token_urlsafe(9),
        repository_id=repository_id,
        user_id=session.user_id,
        plan_id=payload.plan_id,
        request=payload.request,
        status="ready_for_approval",
        proposed_summary="Ready — click Generate patch to create a proposal (no files changed yet).",
    )
    db.add(task); await db.commit(); await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.get("/repositories/{repository_id}/code-tasks", response_model=list[CodeTaskResponse])
async def list_code_tasks(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[CodeTaskResponse]:
    tasks = await db.scalars(select(CodeChangeTask).where(CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id).order_by(CodeChangeTask.created_at.desc()))
    return [CodeTaskResponse.from_task(task) for task in tasks]

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/approve", response_model=CodeTaskResponse)
async def approve_code_task(repository_id: str, task_id: str, payload: CodeTaskDecision, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "patch_ready": raise HTTPException(status_code=409, detail="A patch proposal is required before approval")
    task.status = "approved"; task.approval_note = payload.note; task.approved_at = datetime.now(timezone.utc); await db.commit(); await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/reject", response_model=CodeTaskResponse)
async def reject_code_task(repository_id: str, task_id: str, payload: CodeTaskDecision, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status not in {"ready_for_approval", "patch_ready"}: raise HTTPException(status_code=409, detail="Task is not awaiting decision")
    task.status = "rejected"
    task.approval_note = payload.note
    task.proposed_summary = "Rejected — no repository files were changed."
    await db.commit(); await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/proposal", response_model=CodeTaskResponse)
async def propose_patch(repository_id: str, task_id: str, payload: PatchProposal, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "ready_for_approval": raise HTTPException(status_code=409, detail="Task is not awaiting a patch proposal")
    safe_files = []
    for file in payload.files:
        candidate = Path(file.path)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.name in {"", ".", ".."}:
            raise HTTPException(status_code=422, detail=f"Unsafe patch path: {file.path}")
        safe_files.append({"path": candidate.as_posix(), "content": file.content})
    task.patch_json = json.dumps(safe_files); task.changed_files = json.dumps([file["path"] for file in safe_files]); task.proposed_summary = strip_llm_summary_prefix(payload.summary); task.status = "patch_ready"; await db.commit(); await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/apply", response_model=CodeTaskResponse)
async def apply_patch(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved tasks can be applied")
    root = (Path(settings.repository_data_dir) / repository_id).resolve()
    patch_items = json.loads(task.patch_json or "[]")
    if not patch_items:
        raise HTTPException(status_code=409, detail="This task has no patch content to apply")
    originals: dict[str, str] = {}
    for item in patch_items:
        target = (root / item["path"]).resolve()
        if root not in target.parents and target != root:
            raise HTTPException(status_code=422, detail="Patch path escapes repository workspace")
        if target.exists():
            originals[str(item["path"])] = target.read_text(encoding="utf-8", errors="ignore")
    # Include manifests so quality checks can verify imports against declared deps
    for manifest_name in ("package.json", "pyproject.toml", "requirements.txt"):
        manifest = root / manifest_name
        if manifest_name not in originals and manifest.exists():
            try:
                originals[manifest_name] = manifest.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
    if is_todo_only_patch(
        [{"path": str(item["path"]), "content": str(item["content"])} for item in patch_items],
        originals,
    ) or (
        task.proposed_summary
        and "implementation TODO" in task.proposed_summary.lower()
        and "TODO(Otter)" in json.dumps(patch_items)
    ):
        raise HTTPException(
            status_code=409,
            detail="Refusing to apply a TODO-only stub patch. Regenerate with a working LLM to get a real implementation.",
        )
    try:
        validate_patch_quality(
            task.request,
            [{"path": str(item["path"]), "content": str(item["content"])} for item in patch_items],
            originals,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    writes: list[tuple[Path, str]] = []
    for item in patch_items:
        target = (root / item["path"]).resolve()
        new_content = str(item["content"])
        if target.exists():
            current = target.read_text(encoding="utf-8", errors="ignore")
            if current == new_content:
                continue
        writes.append((target, new_content))
    if not writes:
        task.status = "applied"
        task.applied_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
        return CodeTaskResponse.from_task(task)
    for target, new_content in writes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
    task.status = "applied"
    task.applied_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/generate", response_model=CodeTaskResponse)
async def generate_code_task_patch(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "ready_for_approval":
        raise HTTPException(status_code=409, detail="Task is not ready for patch generation")
    root = Path(settings.repository_data_dir) / repository_id
    words = set(re.findall(r"[a-z0-9_]+", task.request.lower()))
    auth_boost = bool(words & {"auth", "login", "password", "session", "oauth", "signup", "signin", "authentication", "credential"})
    scored_files: list[tuple[float, Path]] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".md"} and path.name not in {"Dockerfile", "Makefile"}:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/").lower()
        score = 0.0
        for word in words:
            if len(word) > 2 and word in rel:
                score += 4.0
        if any(rel.endswith(name) for name in ("main.py", "app.py", "index.ts", "server.ts", "route.ts", "routes.ts")):
            score += 2.0
        if auth_boost and any(term in rel for term in ("auth", "login", "session", "passport", "next-auth", "password", "user", "middleware", "credential")):
            score += 8.0
        scored_files.append((score, path))
    scored_files.sort(key=lambda item: item[0], reverse=True)
    selected = [path for score, path in scored_files if score > 0][:CONTEXT_FILE_LIMIT] or [
        path for _, path in scored_files[:CONTEXT_FILE_LIMIT]
    ]

    intelligence_row = await db.scalar(select(RepositoryIntelligence).where(RepositoryIntelligence.repository_id == repository_id))
    intelligence = None
    if intelligence_row:
        intelligence = {
            "entry_points": json.loads(intelligence_row.entry_points or "[]"),
            "tech_stack": json.loads(intelligence_row.tech_stack or "[]"),
        }
    try:
        plan_context = build_plan(root, task.request, intelligence)
    except Exception:  # noqa: BLE001 — planning is advisory only
        plan_context = {
            "title": f"Plan: {task.request[:80]}",
            "summary": task.request,
            "steps": [],
            "affected_files": [],
            "risks": [],
        }
    for hint in plan_context.get("affected_files") or []:
        candidate = root / str(hint)
        if candidate.is_file() and candidate not in selected:
            selected.insert(0, candidate)

    for extra_name in ("package.json", "pyproject.toml", "requirements.txt", "next.config.js", "next.config.mjs", "next.config.ts"):
        extra = root / extra_name
        if extra.exists() and extra not in selected:
            selected.insert(0, extra)
    # Prefer schema/db/routes for auth work so the small local model sees the real stack.
    if auth_boost:
        for preferred in (
            "shared/schema.ts",
            "server/db.ts",
            "server/routes.ts",
            "server/index.ts",
            "package.json",
        ):
            candidate = root / preferred
            if candidate.is_file() and candidate not in selected:
                selected.insert(0, candidate)
    files = []
    for path in selected[:CONTEXT_FILE_LIMIT]:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
            # Manifests must stay valid JSON/TOML for dependency merging — never truncate.
            if path.name.lower() in {"package.json", "pyproject.toml", "requirements.txt"}:
                content = raw
            else:
                content = raw[:CONTEXT_CHARS_PER_FILE]
            files.append({
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "content": content,
            })
        except OSError:
            continue
    for path in root.rglob("*"):
        if len(files) >= CONTEXT_FILE_LIMIT:
            break
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel in {item["path"] for item in files}:
            continue
        rel_l = rel.lower()
        if (
            rel.endswith(("main.py", "app.py", "server.ts", "server.js", "route.ts", "routes.ts", "schema.ts", "db.ts"))
            or "/api/" in rel_l
            or (auth_boost and any(term in rel_l for term in ("auth", "login", "session", "middleware", "passport")))
        ):
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
                content = raw if path.name.lower() in {"package.json", "pyproject.toml", "requirements.txt"} else raw[:CONTEXT_CHARS_PER_FILE]
                files.append({"path": rel, "content": content})
            except OSError:
                continue
    # Guarantee package.json is present (full text) so dependency auto-merge works.
    pkg = root / "package.json"
    if pkg.is_file() and not any(item["path"] == "package.json" for item in files):
        try:
            files.insert(0, {"path": "package.json", "content": pkg.read_text(encoding="utf-8", errors="ignore")})
            files = files[:CONTEXT_FILE_LIMIT]
        except OSError:
            pass
    files = files[:CONTEXT_FILE_LIMIT]
    try:
        proposal = await generate_patch(task.request, files, plan_context=plan_context)
    except PatchGenerationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 — surface unexpected generate failures
        raise HTTPException(status_code=502, detail=f"Patch generation failed: {error}") from error
    safe_files = []
    for item in proposal["files"]:
        candidate = Path(str(item["path"]))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise HTTPException(status_code=502, detail="Generated patch contained an unsafe path")
        safe_files.append({"path": candidate.as_posix(), "content": str(item["content"])})
    if not safe_files:
        raise HTTPException(status_code=502, detail="Patch generation produced no files")
    originals = {item["path"]: item["content"] for item in files}
    if is_todo_only_patch(safe_files, originals):
        raise HTTPException(
            status_code=502,
            detail="Patch generation produced a TODO-only stub. Fix LLM_MODEL / LLM_API_KEY and regenerate.",
        )
    try:
        validate_patch_quality(task.request, safe_files, originals)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    task.patch_json = json.dumps(safe_files)
    task.changed_files = json.dumps([item["path"] for item in safe_files])
    task.proposed_summary = strip_llm_summary_prefix(str(proposal["summary"]))
    task.status = "patch_ready"
    await db.commit()
    await db.refresh(task)
    return CodeTaskResponse.from_task(task)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/test", response_model=TestResponse)
async def test_code_task(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> TestResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "applied":
        raise HTTPException(status_code=409, detail="Task must be applied before tests can run")
    root = Path(settings.repository_data_dir) / repository_id
    return await __import__("asyncio").to_thread(run_repository_tests, root)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/pull-request", response_model=PullRequestResponse)
async def create_pull_request(repository_id: str, task_id: str, payload: PullRequestRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> PullRequestResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    repository = await store.get(db, session.user_id, repository_id)
    if not task or not repository or task.status != "applied":
        raise HTTPException(status_code=409, detail="Only applied tasks can create pull requests")
    changed_files = json.loads(task.changed_files or "[]")
    if not changed_files:
        raise HTTPException(
            status_code=409,
            detail="This task has no changed files to push. Generate and apply a real patch before opening a PR.",
        )
    patch_blob = task.patch_json or ""
    summary_l = (task.proposed_summary or "").lower()
    if "TODO(Otter)" in patch_blob and (
        "implementation todo" in summary_l
        or "implement carefully" in patch_blob
        or "adds an implementation todo" in summary_l
    ):
        raise HTTPException(
            status_code=409,
            detail="Refusing to open a PR for a TODO-only stub patch. Regenerate a real implementation first.",
        )
    pr_title = strip_llm_summary_prefix(payload.title)
    pr_body = strip_llm_summary_prefix(payload.body)
    if not pr_title or not pr_body:
        raise HTTPException(status_code=422, detail="PR title and body are required")
    parts = repository.url.rstrip("/").removesuffix(".git").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=422, detail="Repository URL cannot identify a GitHub project")
    owner, name = parts[-2], parts[-1]
    root = Path(settings.repository_data_dir) / repository_id
    branch = f"otter/task-{task.id}"
    git_repository = Repo(root)
    await __import__("asyncio").to_thread(git_repository.git.checkout, "-B", branch)
    await __import__("asyncio").to_thread(git_repository.git.add, "--", *changed_files)
    if git_repository.is_dirty(untracked_files=True) or git_repository.index.diff("HEAD"):
        await __import__("asyncio").to_thread(git_repository.index.commit, pr_title)
    remote = git_repository.remote("origin")
    original_url = remote.url
    authenticated_url = github_push_url(original_url, session.github_token)
    try:
        remote.set_url(authenticated_url)
        try:
            await __import__("asyncio").to_thread(remote.push, branch, force=False)
        except GitCommandError as push_error:
            # Branch may already exist with divergent history from a prior attempt — push a unique branch.
            message = str(push_error)
            if "non-fast-forward" in message or "rejected" in message.lower():
                branch = f"otter/task-{task.id}-{token_urlsafe(3)}"
                await __import__("asyncio").to_thread(git_repository.git.checkout, "-B", branch)
                await __import__("asyncio").to_thread(remote.push, branch, force=False)
            else:
                raise
    except GitCommandError as error:
        message = str(error)
        if "403" in message or "Authentication failed" in message or "Permission" in message:
            raise HTTPException(
                status_code=403,
                detail=(
                    "GitHub rejected the push (403). Log out and Connect GitHub again so Otter gets write access, "
                    "and confirm you can push to this repository from your account."
                ),
            ) from error
        raise HTTPException(status_code=502, detail=f"Git push failed: {message[:500]}") from error
    finally:
        remote.set_url(original_url)

    async with httpx.AsyncClient(timeout=30) as client:
        headers = {"Authorization": f"Bearer {session.github_token}", "Accept": "application/vnd.github+json"}
        # Reuse an existing open PR for this head to avoid duplicate PR conflicts.
        existing = await client.get(
            f"{settings.github_api_url}/repos/{owner}/{name}/pulls",
            headers=headers,
            params={"state": "open", "head": f"{owner}:{branch}"},
        )
        if existing.status_code < 400:
            open_prs = existing.json()
            if isinstance(open_prs, list) and open_prs:
                data = open_prs[0]
                return PullRequestResponse(url=data["html_url"], number=data["number"], branch=branch)
        response = await client.post(
            f"{settings.github_api_url}/repos/{owner}/{name}/pulls",
            headers=headers,
            json={"title": pr_title, "body": pr_body, "head": branch, "base": payload.base},
        )
    if response.status_code >= 400:
        detail = response.json().get("message") if response.headers.get("content-type", "").startswith("application/json") else response.text
        # GitHub returns 422 when a PR already exists for the head
        if response.status_code == 422 and "pull request already exists" in str(detail).lower():
            async with httpx.AsyncClient(timeout=30) as client:
                listed = await client.get(
                    f"{settings.github_api_url}/repos/{owner}/{name}/pulls",
                    headers={"Authorization": f"Bearer {session.github_token}", "Accept": "application/vnd.github+json"},
                    params={"state": "open", "head": f"{owner}:{branch}"},
                )
            if listed.status_code < 400 and listed.json():
                data = listed.json()[0]
                return PullRequestResponse(url=data["html_url"], number=data["number"], branch=branch)
        raise HTTPException(status_code=502, detail=f"GitHub rejected pull request creation: {detail}")
    data = response.json()
    return PullRequestResponse(url=data["html_url"], number=data["number"], branch=branch)

@app.get("/repositories/{repository_id}/health", response_model=HealthResponseReport)
async def repository_health(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> HealthResponseReport:
    repository = await store.get(db, session.user_id, repository_id)
    report = await db.get(RepositoryHealth, repository_id)
    if not repository or not report:
        raise HTTPException(status_code=404, detail="Repository health report is not ready")
    return HealthResponseReport(repository_id=repository_id, architecture_score=report.architecture_score, security_score=report.security_score, maintainability_score=report.maintainability_score, performance_score=report.performance_score, debt_score=report.debt_score, documentation_score=report.documentation_score, dependency_score=report.dependency_score, complexity_score=report.complexity_score, findings=json.loads(report.findings), analyzed_at=report.analyzed_at)

@app.get("/repositories/{repository_id}/review", response_model=ReviewResponse)
async def repository_review(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ReviewResponse:
    repository = await store.get(db, session.user_id, repository_id)
    report = await db.scalar(select(RepositoryReview).where(RepositoryReview.repository_id == repository_id, RepositoryReview.user_id == session.user_id).order_by(RepositoryReview.created_at.desc()))
    if not repository or not report: raise HTTPException(status_code=404, detail="Repository review is not ready")
    return ReviewResponse(id=report.id, repository_id=report.repository_id, findings=json.loads(report.findings), created_at=report.created_at)

@app.get("/repositories/{repository_id}/architecture-analysis", response_model=ArchitectureAnalysisResponse)
async def architecture_analysis(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ArchitectureAnalysisResponse:
    if not await store.get(db, session.user_id, repository_id): raise HTTPException(status_code=404, detail="Repository not found")
    report = await db.get(RepositoryArchitectureAnalysis, repository_id)
    if not report: raise HTTPException(status_code=404, detail="Architecture analysis is not ready")
    return ArchitectureAnalysisResponse(repository_id=repository_id, score=report.score, findings=json.loads(report.findings), created_at=report.created_at)

@app.get("/repositories/{repository_id}/performance", response_model=PerformanceResponse)
async def performance(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> PerformanceResponse:
    if not await store.get(db, session.user_id, repository_id): raise HTTPException(status_code=404, detail="Repository not found")
    report = await db.get(RepositoryPerformance, repository_id)
    if not report: raise HTTPException(status_code=404, detail="Performance analysis is not ready")
    return PerformanceResponse(repository_id=repository_id, score=report.score, hotspots=json.loads(report.hotspots), created_at=report.created_at)

def serialize_import_status(job: RepositoryImportJob) -> ImportStatus:
    return ImportStatus(job_id=job.id, repository_id=job.repository_id, status=job.status, attempt_count=job.attempt_count, error=job.error, created_at=job.created_at, started_at=job.started_at, finished_at=job.finished_at)

@app.get("/repositories/{repository_id}/import-status", response_model=ImportStatus)
async def import_status(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ImportStatus:
    job = await store.get_job(db, session.user_id, repository_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return serialize_import_status(job)

@app.post("/repositories/{repository_id}/retry-import", response_model=ImportStatus, status_code=202)
async def retry_import(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ImportStatus:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    job = RepositoryImportJob(id=token_urlsafe(9), repository_id=repository.id, user_id=session.user_id, status="queued")
    repository.status = "queued"; repository.error = None
    db.add(job); await db.commit(); await db.refresh(job)
    enqueue_import(job.id, repository.id)
    return serialize_import_status(job)


@app.post("/internal/github-events")
async def internal_github_events(request: Request) -> dict[str, object]:
    """Receive forwarded GitHub App events for durable processing."""
    expected = os.getenv("OTTER_INTERNAL_TOKEN", "")
    provided = request.headers.get("x-otter-internal-token", "")
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token")
    payload = await request.json()
    event = str(payload.get("event") or "unknown")
    action = None
    nested = payload.get("payload")
    if isinstance(nested, dict):
        action = nested.get("action")
    # Persist-ready hook: currently acknowledge and log shape for workers to extend.
    return {
        "status": "queued",
        "event": event,
        "action": action,
        "delivery": payload.get("delivery"),
        "accepted": True,
    }
