from urllib.parse import urlencode
from secrets import token_urlsafe
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .config import get_settings
from .schemas import HealthResponse, RepositoryCreate, RepositoryListResponse, RepositorySummary
from .store import RepositoryStore

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.next_public_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
store = RepositoryStore()
sessions: dict[str, str] = {}

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
async def github_callback(code: str) -> RedirectResponse:
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    async with httpx.AsyncClient() as client:
        response = await client.post("https://github.com/login/oauth/access_token", data={"client_id": settings.github_client_id, "client_secret": settings.github_client_secret, "code": code}, headers={"Accept": "application/json"})
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub did not return an access token")
    session_id = token_urlsafe(32)
    sessions[session_id] = token
    response = RedirectResponse(settings.next_public_url)
    response.set_cookie("veridexs_session", session_id, httponly=True, samesite="lax", secure=False, max_age=86400)
    return response

@app.get("/auth/me")
async def auth_me(request: Request) -> dict[str, bool]:
    return {"authenticated": request.cookies.get("veridexs_session") in sessions}

def current_access_token(request: Request) -> str:
    session_id = request.cookies.get("veridexs_session")
    token = sessions.get(session_id or "")
    if not token:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    return token

@app.get("/repositories", response_model=RepositoryListResponse)
async def repositories(_: str = Depends(current_access_token)) -> RepositoryListResponse:
    records = await store.list()
    return RepositoryListResponse(repositories=[RepositorySummary.model_validate(record, from_attributes=True) for record in records])

@app.post("/repositories", response_model=RepositorySummary, status_code=202)
async def import_repository(payload: RepositoryCreate, access_token: str = Depends(current_access_token)) -> RepositorySummary:
    if "github.com/" not in payload.url.lower():
        raise HTTPException(status_code=422, detail="Only GitHub repository URLs are supported")
    record = await store.create(payload.url, access_token)
    return RepositorySummary.model_validate(record, from_attributes=True)

@app.get("/repositories/{repository_id}", response_model=RepositorySummary)
async def repository(repository_id: str, _: str = Depends(current_access_token)) -> RepositorySummary:
    record = await store.get(repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositorySummary.model_validate(record, from_attributes=True)
