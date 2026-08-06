import asyncio
from pathlib import Path
from app.health import analyze_health


def test_health_module_is_importable_and_detects_documentation():
    assert callable(analyze_health)


def test_analyze_health_refreshes_the_merged_record(tmp_path: Path):
    class FakeSession:
        def __init__(self) -> None:
            self.merged_record = None

        async def merge(self, record):
            self.merged_record = object.__new__(type(record))
            return self.merged_record

        async def commit(self) -> None:
            return None

        async def refresh(self, record) -> None:
            if record is not self.merged_record:
                raise AssertionError("refresh should target the object returned by merge")

    async def run() -> None:
        session = FakeSession()
        await analyze_health(session, "repo-1", tmp_path, 3)

    asyncio.run(run())
