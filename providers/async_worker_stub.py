"""Deterministic async worker stub for adapter integration tests."""

from __future__ import annotations

import uuid
from typing import Any


class AsyncWorkerStub:
    """In-memory worker implementing the repository's async worker interface."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def submit_job(self, payload: dict[str, Any]) -> dict[str, str]:
        job_id = f"job-{uuid.uuid4()}"
        self._jobs[job_id] = {
            "status": "completed",
            "payload": dict(payload),
            "result": {
                "status": "ok",
                "payload": dict(payload),
            },
        }
        return {"status": "accepted", "job_id": job_id}

    def job_status(self, job_id: str) -> dict[str, str]:
        job = self._jobs.get(job_id)
        if job is None:
            return {"status": "missing", "job_id": job_id}
        return {"status": str(job["status"]), "job_id": job_id}

    def job_result(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            return {"status": "missing", "job_id": job_id}
        result = dict(job["result"])
        result["job_id"] = job_id
        return result


__all__ = ["AsyncWorkerStub"]
