import asyncio
from datetime import datetime, timezone
from pathlib import Path
from celery import Celery
from git import Repo
from sqlalchemy import select
from .config import get_settings
from .database import SessionLocal
from .models import AuthSession, Repository, RepositoryImportJob

settings = get_settings()
celery_app = Celery("veridexs", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True, task_track_started=True, broker_connection_retry_on_startup=True)

def clean_error(error: Exception) -> str:
    message = str(error)
    if settings.github_client_secret:
        message = message.replace(settings.github_client_secret, "[redacted]")
    return message[:1000]

async def process_import(job_id: str, repository_id: str) -> None:
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
