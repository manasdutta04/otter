from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .database import get_db
from .models import AuthSession, Repository, RepositoryImportJob, RepositoryIntelligence, User
from .schemas import ChatRequest, ChatResponse, HealthResponse, ImportStatus, IntelligenceResponse, RepositoryCreate, RepositoryListResponse, RepositorySummary
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
