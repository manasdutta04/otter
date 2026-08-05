from app.worker import clean_error, import_repository_task

def test_clean_error_redacts_github_secret(monkeypatch):
    monkeypatch.setattr("app.worker.settings.github_client_secret", "super-secret")
    assert "super-secret" not in clean_error(RuntimeError("clone failed with super-secret"))
    assert "[redacted]" in clean_error(RuntimeError("clone failed with super-secret"))

def test_import_task_payload_contains_only_ids():
    assert import_repository_task.name == "repositories.import"
    assert import_repository_task.max_retries == 3
