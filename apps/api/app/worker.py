import asyncio
from datetime import datetime, timezone
from pathlib import Path
from celery import Celery
from git import Repo
from sqlalchemy import select
from .config import get_settings
from .database import get_session_factory
from .models import AuthSession, Repository, RepositoryImportJob
from .analyzer import inspect_repository, save_intelligence
from .graph import build_graph, save_graph
from .health import analyze_health
from .review import review_repository, save_review
from .architecture_analysis import analyze_architecture
from .performance import analyze_performance

settings = get_settings()
celery_app = Celery("otter", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, task_track_started=True, broker_connection_retry_on_startup=True)


def redis_available(timeout: float = 0.4) -> bool:
    """True when the Celery broker (Redis) accepts a TCP connection."""
    from urllib.parse import urlparse
    import socket

    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def enqueue_import(job_id: str, repository_id: str) -> str:
    """Queue via Celery when Redis is up; otherwise run in-process (native/no-Docker)."""
    if redis_available():
        import_repository_task.delay(job_id, repository_id)
        return "celery"
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(process_import(job_id, repository_id))
        return "inline"
    loop.create_task(process_import(job_id, repository_id))
    return "background"


def clean_error(error: Exception) -> str:
    message = str(error)
    if settings.github_client_secret:
        message = message.replace(settings.github_client_secret, "[redacted]")
    return message[:1000]

async def process_import(job_id: str, repository_id: str) -> None:
    SessionLocal = get_session_factory()
    async with SessionLocal() as db:
        job = await db.get(RepositoryImportJob, job_id)
        repository = await db.get(Repository, repository_id)
        if not job or not repository:
            return
        token_result = await db.execute(select(AuthSession.github_token).where(AuthSession.user_id == job.user_id, AuthSession.expires_at > datetime.now(timezone.utc)).order_by(AuthSession.expires_at.desc()).limit(1))
        token = token_result.scalar_one_or_none()
        if not token:
            job.status = "failed"; job.error = "No active GitHub session is available"; job.finished_at = datetime.now(timezone.utc); repository.status = "failed"; repository.error = job.error; await db.commit(); return
        job.status = "running"; job.attempt_count += 1; job.started_at = datetime.now(timezone.utc); job.error = None; repository.status = "cloning"; repository.error = None; await db.commit()
    destination = Path(settings.repository_data_dir) / repository_id
    try:
        if destination.exists():
            import shutil
            await asyncio.to_thread(shutil.rmtree, destination)
        clone_url = repository.url.replace("https://github.com/", f"https://x-access-token:{token}@github.com/", 1)
        await asyncio.to_thread(Repo.clone_from, clone_url, destination, depth=1)
        files = [path for path in destination.rglob("*") if path.is_file() and ".git" not in path.parts]
        git_repository = await asyncio.to_thread(Repo, destination)
        async with SessionLocal() as db:
            job = await db.get(RepositoryImportJob, job_id); repository = await db.get(Repository, repository_id)
            intel = await asyncio.to_thread(inspect_repository, destination)
            try:
                from app.intelligence.explain import explain_analysis, merge_explanation_into_legacy

                analysis = intel.get("analysis") if isinstance(intel.get("analysis"), dict) else {}
                explanation = await explain_analysis(analysis)
                intel = merge_explanation_into_legacy(intel, explanation)
            except Exception as explain_error:  # noqa: BLE001 — analysis still saved without LLM prose
                import logging

                logging.getLogger(__name__).warning("Intelligence explain skipped: %s", explain_error)
            await save_intelligence(db, repository_id, intel)
            nodes, edges = await asyncio.to_thread(build_graph, destination)
            await save_graph(db, repository_id, nodes, edges)
            await analyze_health(db, repository_id, destination, len(files))
            await save_review(db, repository_id, repository.user_id, await asyncio.to_thread(review_repository, destination))
            await analyze_architecture(db, repository_id, destination)
            await analyze_performance(db, repository_id, destination)
            job.status = "succeeded"; job.finished_at = datetime.now(timezone.utc); repository.status = "ready"; repository.branch = git_repository.active_branch.name; repository.file_count = len(files); await db.commit()
    except Exception as error:
        async with SessionLocal() as db:
            job = await db.get(RepositoryImportJob, job_id); repository = await db.get(Repository, repository_id)
            job.status = "failed"; job.finished_at = datetime.now(timezone.utc); job.error = clean_error(error); repository.status = "failed"; repository.error = job.error; await db.commit()
        raise

@celery_app.task(bind=True, max_retries=3, name="repositories.import")
def import_repository_task(self, job_id: str, repository_id: str) -> None:
    try:
        asyncio.run(process_import(job_id, repository_id))
    except Exception as error:
        raise self.retry(exc=error, countdown=2 ** self.request.retries) from error
