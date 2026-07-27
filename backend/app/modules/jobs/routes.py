"""Rutas de jobs."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.saas import JobStatus
from app.modules.deps import get_current_user_id, get_job_queue
from app.modules.jobs.schemas import JobEnqueueRequest, JobProcessResponse, JobRead
from app.modules.jobs.service import JobsService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_jobs_service() -> JobsService:
    return JobsService(get_job_queue())


@router.post("", response_model=JobRead, status_code=201)
def enqueue_job(
    body: JobEnqueueRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: JobsService = Depends(get_jobs_service),
):
    return service.enqueue(
        db,
        tipo=body.tipo,
        payload=body.payload,
        user_id=user_id,
        max_attempts=body.max_attempts,
    )


@router.get("", response_model=List[JobRead])
def list_jobs(
    status: Optional[JobStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    service: JobsService = Depends(get_jobs_service),
):
    return service.list_jobs(db, status=status, limit=limit)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    service: JobsService = Depends(get_jobs_service),
):
    return service.get(db, job_id)


@router.post("/process-next", response_model=JobProcessResponse)
def process_next(
    db: Session = Depends(get_db),
    service: JobsService = Depends(get_jobs_service),
):
    job = service.process_next(db)
    if not job:
        return JobProcessResponse(processed=False)
    return JobProcessResponse(processed=True, job=JobRead.model_validate(job))
