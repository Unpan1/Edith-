"""Schemas Pydantic para transcripciones."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class TranscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    texto: str
    idioma: Optional[str] = None
    segmentos: Optional[List[Any]] = None
    fecha: datetime
