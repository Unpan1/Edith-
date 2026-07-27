"""Schemas de tendencias."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class TrendReportRead(BaseModel):
    id: int
    category: str
    country: str
    title: str
    score: float
    opportunity_score: float
    data: Optional[Any] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class TrendsResponse(BaseModel):
    items: List[TrendReportRead]
