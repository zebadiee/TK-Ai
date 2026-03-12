"""TK-Ai workflow scheduler."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hades.kernel import build_default_kernel

try:
    import croniter as croniter_module
except ImportError:  # pragma: no cover - exercised through fallback matching tests
    croniter_module = None


class WorkflowScheduler:
    """Dispatches kernel intents from cron-like schedule definitions."""

    def __init__(self, repo_root: Path, schedule_file: Path, kernel: Any | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.schedule_file = Path(schedule_file)
        self.kernel = kernel or build_default_kernel(self.repo_root)
        self.jobs: list[dict[str, Any]] = []
        self._last_run_slots: dict[str, datetime] = {}

    def load(self) -> None:
        data = json.loads(self.schedule_file.read_text(encoding="utf-8"))
        raw_jobs = data.get("jobs", []) if isinstance(data, dict) else []
        if not isinstance(raw_jobs, list):
            self.jobs = []
            return

        jobs: list[dict[str, Any]] = []
        for index, raw_job in enumerate(raw_jobs):
            if not isinstance(raw_job, dict):
                continue

            schedule = str(raw_job.get("schedule", "")).strip()
            intent = str(raw_job.get("intent", "")).strip()
            if not schedule or not intent:
                continue

            jobs.append(
                {
                    "id": str(raw_job.get("id", f"job-{index + 1}")),
                    "schedule": schedule,
                    "intent": intent,
                }
            )

        self.jobs = jobs

    def run_once(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        else:
            current_time = current_time.astimezone(timezone.utc)

        slot = current_time.replace(second=0, microsecond=0)
        results: list[dict[str, Any]] = []

        for job in self.jobs:
            job_id = str(job["id"])
            schedule = str(job["schedule"])
            intent = str(job["intent"])
            if not self._matches_schedule(schedule, slot):
                continue
            if self._last_run_slots.get(job_id) == slot:
                continue

            trace_id = f"scheduler-{job_id}-{self._slug(intent)}-{slot.strftime('%Y%m%dT%H%MZ')}"
            result = self.kernel.handle_intent(
                {
                    "intent": intent,
                    "payload": {
                        "trace_id": trace_id,
                        "schedule": schedule,
                        "scheduled_at": slot.isoformat(),
                        "scheduler_job_id": job_id,
                    },
                }
            )
            self._last_run_slots[job_id] = slot
            results.append(result)
            print("scheduler_result:", result)

        return results

    def run_forever(self, interval: int = 30) -> None:
        while True:
            self.run_once()
            time.sleep(interval)

    def _matches_schedule(self, schedule: str, now: datetime) -> bool:
        if croniter_module is not None and hasattr(croniter_module, "croniter"):
            croniter_type = croniter_module.croniter
            matcher = getattr(croniter_type, "match", None)
            if callable(matcher):
                return bool(matcher(schedule, now))
        return _matches_five_field_cron(schedule, now)

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "intent"


def _matches_five_field_cron(schedule: str, now: datetime) -> bool:
    fields = schedule.split()
    if len(fields) != 5:
        raise ValueError(f"Unsupported cron expression: {schedule!r}")

    minute, hour, day, month, weekday = fields
    return all(
        (
            _match_field(minute, now.minute, 0, 59),
            _match_field(hour, now.hour, 0, 23),
            _match_field(day, now.day, 1, 31),
            _match_field(month, now.month, 1, 12),
            _match_field(weekday, (now.weekday() + 1) % 7, 0, 6),
        )
    )


def _match_field(field: str, value: int, minimum: int, maximum: int) -> bool:
    return any(_match_part(part, value, minimum, maximum) for part in field.split(","))


def _match_part(part: str, value: int, minimum: int, maximum: int) -> bool:
    step = 1
    base = part.strip()
    if not base:
        return False

    if "/" in base:
        base, step_text = base.split("/", 1)
        step = int(step_text)
        if step <= 0:
            raise ValueError(f"Invalid cron step: {part!r}")

    if base in {"*", ""}:
        start = minimum
        end = maximum
    elif "-" in base:
        start_text, end_text = base.split("-", 1)
        start = int(start_text)
        end = int(end_text)
    else:
        start = int(base)
        end = int(base)

    if start < minimum or end > maximum or start > end:
        raise ValueError(f"Invalid cron range: {part!r}")
    if value < start or value > end:
        return False
    return (value - start) % step == 0


__all__ = ["WorkflowScheduler"]
