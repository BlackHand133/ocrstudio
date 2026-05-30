"""Tiny in-process job registry for long-running work (batch detect, export).

Single-user scope: jobs live in memory and are polled via GET /api/jobs/{id}.
Thread-safe so background worker threads can update progress.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional
import uuid


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, job_type: str, total: int = 0) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "running",  # running | done | error
                "total": total,
                "done": 0,
                "message": "",
                "result": None,
                "error": None,
            }
        return job_id

    def update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.update(fields)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None


jobs = JobRegistry()
