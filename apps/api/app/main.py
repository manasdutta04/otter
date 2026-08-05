from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import AuthSession, User
from .schemas import HealthResponse, RepositoryCreate, RepositoryListResponse, RepositorySummary
from .store import RepositoryStore

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.next_public_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
store = RepositoryStore()

@app.on_event("startup")
async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

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

@app.get("/repositories", response_model=RepositoryListResponse)
async def repositories(session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositoryListResponse:
    records = await store.list(db, session.user_id)
    return RepositoryListResponse(repositories=[RepositorySummary.model_validate(record, from_attributes=True) for record in records])

@app.post("/repositories", response_model=RepositorySummary, status_code=202)
async def import_repository(payload: RepositoryCreate, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositorySummary:
    if "github.com/" not in payload.url.lower():
        raise HTTPException(status_code=422, detail="Only GitHub repository URLs are supported")
    record = await store.create(db, session.user_id, payload.url, session.github_token)
    return RepositorySummary.model_validate(record, from_attributes=True)

@app.get("/repositories/{repository_id}", response_model=RepositorySummary)
async def repository(repository_id: str, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)) -> RepositorySummary:
    record = await store.get(db, session.user_id, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositorySummary.model_validate(record, from_attributes=True)
