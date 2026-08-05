from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import json
import subprocess
from pathlib import Path
import httpx
from git import Repo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .database import get_db
from .models import AuthSession, CodeChangeTask, GeneratedDocument, MemoryEntry, Repository, RepositoryGraph, RepositoryHealth, RepositoryImportJob, RepositoryIntelligence, RepositoryPlan, User
from .knowledge import add_memory, generate_overview
from .llm import generate_patch
from .planner import build_plan, save_plan
from .schemas import ArchitectureGraphResponse, ChatRequest, ChatResponse, CodeTaskCreate, CodeTaskDecision, CodeTaskResponse, DocumentResponse, HealthResponse, HealthResponseReport, ImportStatus, IntelligenceResponse, MemoryCreate, MemoryResponse, PatchProposal, PlanRequest, PlanResponse, PullRequestRequest, PullRequestResponse, RepositoryCreate, RepositoryListResponse, RepositorySummary, TestResponse
from .health import analyze_health
from .store import RepositoryStore
from .worker import import_repository_task

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.next_public_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
store = RepositoryStore()

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")

@app.get("/auth/github/login")
async def github_login() -> RedirectResponse:
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    params = urlencode({"client_id": settings.github_client_id, "redirect_uri": settings.github_redirect_uri, "scope": "read:user repo"})
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")

@app.get("/auth/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)) -> RedirectResponse:
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
        user = User(id=token_urlsafe(16), github_id=str(github_user["id"]), login=github_user["login"], avatar_url=github_user.get("avatar_url"))
        db.add(user)
    else:
        user.login = github_user["login"]
        user.avatar_url = github_user.get("avatar_url")
    session_id = token_urlsafe(32)
    db.add(AuthSession(id=session_id, user_id=user.id, github_token=token, expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
    await db.commit()
    redirect = RedirectResponse(settings.next_public_url)
    redirect.set_cookie("veridexs_session", session_id, httponly=True, samesite="lax", secure=False, max_age=86400)
    return redirect

async def current_session(request: Request, db: AsyncSession = Depends(get_db)) -> AuthSession:
    session_id = request.cookies.get("veridexs_session")
    session = await db.get(AuthSession, session_id or "")
    if not session or session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    return session

@app.get("/auth/me")
async def auth_me(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    try:
        await current_session(request, db)
        return {"authenticated": True}
    except HTTPException:
        return {"authenticated": False}

@app.post("/auth/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    session_id = request.cookies.get("veridexs_session")
    if session_id:
        session = await db.get(AuthSession, session_id)
        if session:
            await db.delete(session)
            await db.commit()
    response = Response(status_code=204)
    response.delete_cookie("veridexs_session")
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
    import_repository_task.delay(job.id, record.id)
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
    return IntelligenceResponse(repository_id=repository_id, summary=record.summary, tech_stack=json.loads(record.tech_stack), folders=json.loads(record.folders), entry_points=json.loads(record.entry_points), architecture_signals=json.loads(record.architecture_signals), analyzed_at=record.analyzed_at)

@app.post("/repositories/{repository_id}/chat", response_model=ChatResponse)
async def repository_chat(repository_id: str, payload: ChatRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ChatResponse:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must finish importing before chat is available")
    root = Path(settings.repository_data_dir) / repository_id
    question = payload.question.lower()
    matches: list[str] = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts and any(term in path.name.lower() or term in str(path.parent).lower() for term in question.split() if len(term) > 3):
            matches.append(str(path.relative_to(root)).replace("\\", "/"))
    matches = matches[:8]
    intelligence_record = await db.get(RepositoryIntelligence, repository_id)
    if "auth" in question or "login" in question:
        answer = "Authentication-related files are the strongest matches I found. Review these files first: " + ", ".join(matches) if matches else "I could not find an obvious authentication path in the indexed file names."
    elif "folder" in question or "structure" in question or "architecture" in question:
        folders = json.loads(intelligence_record.folders) if intelligence_record else []
        answer = "The repository is organized around these folders: " + ", ".join(folders[:12]) if folders else "Repository structure is not indexed yet."
    else:
        answer = "I found these likely relevant files: " + ", ".join(matches) if matches else "I did not find a strong filename match. Ask about a concrete subsystem such as authentication, API, tests, or folder structure."
    return ChatResponse(answer=answer, sources=matches)

@app.post("/repositories/{repository_id}/plans", response_model=PlanResponse, status_code=201)
async def create_plan(repository_id: str, payload: PlanRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> PlanResponse:
    repository = await store.get(db, session.user_id, repository_id)
    intelligence_record = await db.get(RepositoryIntelligence, repository_id)
    if not repository or repository.status != "ready":
        raise HTTPException(status_code=409, detail="Repository must finish importing before planning is available")
    intelligence = {"entry_points": json.loads(intelligence_record.entry_points)} if intelligence_record else None
    plan = await save_plan(db, repository_id, session.user_id, payload.request, build_plan(Path(settings.repository_data_dir) / repository_id, payload.request, intelligence))
    return PlanResponse(id=plan.id, repository_id=plan.repository_id, request=plan.request, title=plan.title, complexity=plan.complexity, summary=plan.summary, steps=json.loads(plan.steps), affected_files=json.loads(plan.affected_files), dependencies=json.loads(plan.dependencies), risks=json.loads(plan.risks), created_at=plan.created_at)

@app.get("/repositories/{repository_id}/plans", response_model=list[PlanResponse])
async def list_plans(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[PlanResponse]:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    records = await db.scalars(select(RepositoryPlan).where(RepositoryPlan.repository_id == repository_id, RepositoryPlan.user_id == session.user_id).order_by(RepositoryPlan.created_at.desc()))
    return [PlanResponse(id=plan.id, repository_id=plan.repository_id, request=plan.request, title=plan.title, complexity=plan.complexity, summary=plan.summary, steps=json.loads(plan.steps), affected_files=json.loads(plan.affected_files), dependencies=json.loads(plan.dependencies), risks=json.loads(plan.risks), created_at=plan.created_at) for plan in records]

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
    task = CodeChangeTask(id=token_urlsafe(9), repository_id=repository_id, user_id=session.user_id, plan_id=payload.plan_id, request=payload.request, status="ready_for_approval", proposed_summary="The requested change is captured and awaits human approval before any source file can be modified.")
    db.add(task); await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

@app.get("/repositories/{repository_id}/code-tasks", response_model=list[CodeTaskResponse])
async def list_code_tasks(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> list[CodeTaskResponse]:
    tasks = await db.scalars(select(CodeChangeTask).where(CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id).order_by(CodeChangeTask.created_at.desc()))
    return [CodeTaskResponse.model_validate(task, from_attributes=True) for task in tasks]

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/approve", response_model=CodeTaskResponse)
async def approve_code_task(repository_id: str, task_id: str, payload: CodeTaskDecision, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "patch_ready": raise HTTPException(status_code=409, detail="A patch proposal is required before approval")
    task.status = "approved"; task.approval_note = payload.note; task.approved_at = datetime.now(timezone.utc); await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/reject", response_model=CodeTaskResponse)
async def reject_code_task(repository_id: str, task_id: str, payload: CodeTaskDecision, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status not in {"ready_for_approval", "patch_ready"}: raise HTTPException(status_code=409, detail="Task is not awaiting decision")
    task.status = "rejected"; task.approval_note = payload.note; await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

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
    task.patch_json = json.dumps(safe_files); task.changed_files = json.dumps([file["path"] for file in safe_files]); task.proposed_summary = payload.summary; task.status = "patch_ready"; await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/apply", response_model=CodeTaskResponse)
async def apply_patch(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "approved": raise HTTPException(status_code=409, detail="Only approved tasks can be applied")
    root = (Path(settings.repository_data_dir) / repository_id).resolve()
    for item in json.loads(task.patch_json):
        target = (root / item["path"]).resolve()
        if root not in target.parents and target != root: raise HTTPException(status_code=422, detail="Patch path escapes repository workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
    task.status = "applied"; task.applied_at = datetime.now(timezone.utc); await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/generate", response_model=CodeTaskResponse)
async def generate_code_task_patch(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> CodeTaskResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "ready_for_approval": raise HTTPException(status_code=409, detail="Task is not ready for patch generation")
    root = Path(settings.repository_data_dir) / repository_id
    files = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts and len(files) < 20:
            files.append({"path": str(path.relative_to(root)).replace("\\", "/"), "content": path.read_text(encoding="utf-8", errors="ignore")})
    proposal = await generate_patch(task.request, files)
    safe_files = []
    for item in proposal["files"]:
        candidate = Path(str(item["path"]))
        if candidate.is_absolute() or ".." in candidate.parts: raise HTTPException(status_code=502, detail="LLM returned an unsafe patch path")
        safe_files.append({"path": candidate.as_posix(), "content": str(item["content"])})
    task.patch_json = json.dumps(safe_files); task.changed_files = json.dumps([item["path"] for item in safe_files]); task.proposed_summary = str(proposal["summary"]); task.status = "patch_ready"; await db.commit(); await db.refresh(task)
    return CodeTaskResponse.model_validate(task, from_attributes=True)

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/test", response_model=TestResponse)
async def test_code_task(repository_id: str, task_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> TestResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    if not task or task.status != "applied": raise HTTPException(status_code=409, detail="Task must be applied before tests can run")
    root = Path(settings.repository_data_dir) / repository_id
    try:
        result = subprocess.run(["python", "-m", "pytest", "-q"], cwd=root, capture_output=True, text=True, timeout=120)
        output = (result.stdout + "\n" + result.stderr)[-12000:]
        return TestResponse(passed=result.returncode == 0, output=output)
    except (OSError, subprocess.TimeoutExpired) as error:
        return TestResponse(passed=False, output=str(error))

@app.post("/repositories/{repository_id}/code-tasks/{task_id}/pull-request", response_model=PullRequestResponse)
async def create_pull_request(repository_id: str, task_id: str, payload: PullRequestRequest, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> PullRequestResponse:
    task = await db.scalar(select(CodeChangeTask).where(CodeChangeTask.id == task_id, CodeChangeTask.repository_id == repository_id, CodeChangeTask.user_id == session.user_id))
    repository = await store.get(db, session.user_id, repository_id)
    if not task or not repository or task.status != "applied": raise HTTPException(status_code=409, detail="Only applied tasks can create pull requests")
    parts = repository.url.rstrip("/").removesuffix(".git").split("/")
    if len(parts) < 2: raise HTTPException(status_code=422, detail="Repository URL cannot identify a GitHub project")
    owner, name = parts[-2], parts[-1]
    root = Path(settings.repository_data_dir) / repository_id
    branch = f"veridexs/task-{task.id}"
    git_repository = Repo(root)
    await __import__("asyncio").to_thread(git_repository.git.checkout, "-B", branch)
    await __import__("asyncio").to_thread(git_repository.git.add, "--", *json.loads(task.changed_files))
    await __import__("asyncio").to_thread(git_repository.index.commit, payload.title)
    remote = git_repository.remote("origin")
    original_url = remote.url
    authenticated_url = original_url.replace("https://github.com/", f"https://x-access-token:{session.github_token}@github.com/", 1)
    try:
        remote.set_url(authenticated_url)
        await __import__("asyncio").to_thread(remote.push, branch)
    finally:
        remote.set_url(original_url)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{settings.github_api_url}/repos/{owner}/{name}/pulls", headers={"Authorization": f"Bearer {session.github_token}", "Accept": "application/vnd.github+json"}, json={"title": payload.title, "body": payload.body, "head": branch, "base": payload.base})
    if response.status_code >= 400: raise HTTPException(status_code=502, detail="GitHub rejected pull request creation")
    data = response.json()
    return PullRequestResponse(url=data["html_url"], number=data["number"], branch=branch)

@app.get("/repositories/{repository_id}/health", response_model=HealthResponseReport)
async def repository_health(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> HealthResponseReport:
    repository = await store.get(db, session.user_id, repository_id)
    report = await db.get(RepositoryHealth, repository_id)
    if not repository or not report:
        raise HTTPException(status_code=404, detail="Repository health report is not ready")
    return HealthResponseReport(repository_id=repository_id, architecture_score=report.architecture_score, security_score=report.security_score, maintainability_score=report.maintainability_score, performance_score=report.performance_score, debt_score=report.debt_score, documentation_score=report.documentation_score, dependency_score=report.dependency_score, complexity_score=report.complexity_score, findings=json.loads(report.findings), analyzed_at=report.analyzed_at)

@app.get("/repositories/{repository_id}/import-status", response_model=ImportStatus)
async def import_status(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ImportStatus:
    job = await store.get_job(db, session.user_id, repository_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportStatus.model_validate(job, from_attributes=True)

@app.post("/repositories/{repository_id}/retry-import", response_model=ImportStatus, status_code=202)
async def retry_import(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> ImportStatus:
    repository = await store.get(db, session.user_id, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    job = RepositoryImportJob(id=token_urlsafe(9), repository_id=repository.id, user_id=session.user_id, status="queued")
    repository.status = "queued"; repository.error = None
    db.add(job); await db.commit(); await db.refresh(job)
    import_repository_task.delay(job.id, repository.id)
    return ImportStatus.model_validate(job, from_attributes=True)
