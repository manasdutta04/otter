from datetime import datetime, timezone
from app.main import serialize_import_status
from app.models import RepositoryImportJob


def test_serialize_import_status_maps_job_id_from_orm_object():
    job = RepositoryImportJob(
        id="job-1",
        repository_id="repo-1",
        user_id="user-1",
        status="queued",
        attempt_count=2,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        created_at=datetime.now(timezone.utc),
    )

    status = serialize_import_status(job)

    assert status.job_id == "job-1"
    assert status.repository_id == "repo-1"
    assert status.attempt_count == 2
