"""Schemas de automatización."""

from typing import List, Optional

from pydantic import BaseModel, Field


class AutomationSettingsRead(BaseModel):
    user_id: int
    enrich_after_process: bool = True
    auto_schedule_stubs: bool = False
    auto_thumbnails: bool = True
    default_platforms: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class AutomationSettingsUpdate(BaseModel):
    enrich_after_process: Optional[bool] = None
    auto_schedule_stubs: Optional[bool] = None
    auto_thumbnails: Optional[bool] = None
    default_platforms: Optional[List[str]] = Field(default=None)
