from datetime import datetime, timezone
from pathlib import Path

from hades.scheduler import WorkflowScheduler
from kernel.scheduler import WorkflowScheduler as PublicWorkflowScheduler


class StubKernel:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def handle_intent(self, message: dict[str, object]) -> dict[str, object]:
        self.calls.append(message)
        return {"status": "accepted", "intent": message["intent"]}


def test_scheduler_loads_jobs(tmp_path: Path) -> None:
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(
        '{"jobs":[{"schedule":"* * * * *","intent":"analyse btc funding rates"}]}',
        encoding="utf-8",
    )

    scheduler = WorkflowScheduler(tmp_path, schedule_file, kernel=StubKernel())
    scheduler.load()

    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0]["intent"] == "analyse btc funding rates"


def test_scheduler_dispatches_due_job_only_once_per_slot(tmp_path: Path) -> None:
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(
        '{"jobs":[{"id":"btc-watch","schedule":"*/5 * * * *","intent":"monitor btc funding rates"}]}',
        encoding="utf-8",
    )
    kernel = StubKernel()
    scheduler = WorkflowScheduler(tmp_path, schedule_file, kernel=kernel)
    scheduler.load()
    now = datetime(2026, 3, 11, 10, 15, 0, tzinfo=timezone.utc)

    first = scheduler.run_once(now=now)
    second = scheduler.run_once(now=now)

    assert len(first) == 1
    assert second == []
    assert len(kernel.calls) == 1
    assert kernel.calls[0]["intent"] == "monitor btc funding rates"


def test_scheduler_skips_jobs_outside_matching_slot(tmp_path: Path) -> None:
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(
        '{"jobs":[{"schedule":"0 * * * *","intent":"summarise ethereum market activity"}]}',
        encoding="utf-8",
    )
    kernel = StubKernel()
    scheduler = WorkflowScheduler(tmp_path, schedule_file, kernel=kernel)
    scheduler.load()

    result = scheduler.run_once(now=datetime(2026, 3, 11, 10, 15, 0, tzinfo=timezone.utc))

    assert result == []
    assert kernel.calls == []


def test_public_scheduler_facade_points_to_runtime() -> None:
    assert PublicWorkflowScheduler is WorkflowScheduler
