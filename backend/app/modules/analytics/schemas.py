"""Schemas de analytics."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.saas import Platform


class AnalyticsSnapshotCreate(BaseModel):
    clip_id: Optional[int] = None
    video_id: Optional[int] = None
    platform: Optional[Platform] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_sec: float = 0.0


class AnalyticsSnapshotRead(BaseModel):
    id: int
    user_id: int
    clip_id: Optional[int] = None
    video_id: Optional[int] = None
    platform: Optional[Platform] = None
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_sec: float
    fecha: datetime

    model_config = {"from_attributes": True}


class RankingItem(BaseModel):
    clip_id: Optional[int] = None
    video_id: Optional[int] = None
    score: float
    views: int
    likes: int


class RankingResponse(BaseModel):
    items: List[RankingItem] = Field(default_factory=list)
