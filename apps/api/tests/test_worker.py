import asyncio
from app import database
from app.worker import clean_error, import_repository_task

def test_clean_error_redacts_github_secret(monkeypatch):
    monkeypatch.setattr("app.worker.settings.github_client_secret", "super-secret")
    assert "super-secret" not in clean_error(RuntimeError("clone failed with super-secret"))
    assert "[redacted]" in clean_error(RuntimeError("clone failed with super-secret"))

def test_import_task_payload_contains_only_ids():
    assert import_repository_task.name == "repositories.import"
    assert import_repository_task.max_retries == 3


def test_session_factory_is_created_per_event_loop():
    database._engine_cache.clear()

    async def build_factory():
        return database.get_session_factory()

    factory_a = asyncio.run(build_factory())
    factory_b = asyncio.run(build_factory())

    assert factory_a is not factory_b
