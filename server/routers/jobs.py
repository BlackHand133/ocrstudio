"""Job status polling."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.jobs import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job
