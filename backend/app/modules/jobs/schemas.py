"""Schemas de jobs."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.saas import JobStatus


class JobEnqueueRequest(BaseModel):
    tipo: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = 3


class JobRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    tipo: str
    payload: Optional[Any] = None
    status: JobStatus
    attempts: int
    max_attempts: int
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobProcessResponse(BaseModel):
    processed: bool
    job: Optional[JobRead] = None
    queue_job_id: Optional[str] = None
