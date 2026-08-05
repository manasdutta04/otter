from app.schemas import CodeTaskCreate, CodeTaskDecision

def test_code_task_requires_explicit_request():
    task = CodeTaskCreate(request="Add a health endpoint")
    assert task.plan_id is None
    assert CodeTaskDecision(note="reviewed").note == "reviewed"
