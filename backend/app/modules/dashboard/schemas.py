"""Schemas del dashboard."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RecentClipItem(BaseModel):
    id: int
    titulo: Optional[str] = None
    duracion: float = 0
    score: float = 0
    formato: Optional[str] = None
    fecha: Optional[datetime] = None


class DashboardStats(BaseModel):
    videos: int = 0
    videos_completed: int = 0
    clips: int = 0
    minutes_processed: float = 0
    time_saved_hours: float = 0
    jobs_queued: int = 0
    jobs_processing: int = 0
    scheduled_posts: int = 0
    published_posts: int = 0
    credits_balance: int = 0
    credits_used_month: int = 0
    notifications_unread: int = 0
    recent_clips: List[RecentClipItem] = Field(default_factory=list)
