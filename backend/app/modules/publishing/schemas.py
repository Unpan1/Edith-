"""Schemas de publicación."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.models.saas import Platform, PostStatus


class ScheduledPostCreate(BaseModel):
    clip_id: Optional[int] = None
    platform: Platform
    status: PostStatus = PostStatus.DRAFT
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None


class ScheduledPostUpdate(BaseModel):
    status: Optional[PostStatus] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScheduledPostRead(BaseModel):
    id: int
    user_id: int
    clip_id: Optional[int] = None
    platform: Platform
    status: PostStatus
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    hashtags: Optional[Any] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class SocialAccountConnect(BaseModel):
    platform: Platform
    handle: str = Field(..., min_length=1)


class SocialAccountRead(BaseModel):
    id: int
    user_id: int
    platform: Platform
    handle: Optional[str] = None
    connected: bool

    model_config = {"from_attributes": True}
