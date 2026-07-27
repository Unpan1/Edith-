"""Schemas de admin."""

from typing import Any, List

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    nombre: str
    email: str

    model_config = {"from_attributes": True}


class AdminJobItem(BaseModel):
    id: int
    tipo: str
    status: str
    attempts: int
    error: Any = None

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    users: int = 0
    videos: int = 0
    clips: int = 0
    jobs: int = 0
    scheduled_posts: int = 0
    plans: int = 0


class AdminOverview(BaseModel):
    stats: SystemStats
    users: List[AdminUserItem] = []
    recent_jobs: List[AdminJobItem] = []
