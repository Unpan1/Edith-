"""Schemas de calendario."""

from typing import List

from pydantic import BaseModel

from app.modules.publishing.schemas import ScheduledPostRead


class CalendarMonthResponse(BaseModel):
    year: int
    month: int
    posts: List[ScheduledPostRead] = []
