"""Schemas del growth agent."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GrowthPlanRequest(BaseModel):
    instruction: str = Field(..., min_length=3)
    video_id: int


class GrowthPlanResult(BaseModel):
    video_id: int
    instruction: str
    platforms: List[str]
    suggested_options: Dict[str, Any]
    schedule_stubs: List[Dict[str, Any]] = []
    notes: List[str] = []
    job_id: Optional[int] = None


class GrowthEnqueueResponse(BaseModel):
    job_id: int
    message: str = "Plan de growth encolado"
