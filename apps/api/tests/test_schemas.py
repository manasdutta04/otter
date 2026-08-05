from datetime import datetime, timezone
from app.schemas import ImportStatus

def test_import_status_accepts_durable_lifecycle_fields():
    status = ImportStatus(job_id="job-1", repository_id="repo-1", status="queued", attempt_count=0, created_at=datetime.now(timezone.utc))
    assert status.status == "queued"
