"""Schemas de learning."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LearningInsightRead(BaseModel):
    id: int
    user_id: int
    clip_id: Optional[int] = None
    insight_type: str
    titulo: str
    detalle: str
    score: float
    fecha: datetime

    model_config = {"from_attributes": True}


class LearningGenerateResponse(BaseModel):
    insights: List[LearningInsightRead]
