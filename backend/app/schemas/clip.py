"""Schemas Pydantic para clips."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    inicio: float
    fin: float
    duracion: float
    ruta_clip: str
    ruta_miniatura: Optional[str] = None
    ruta_srt: Optional[str] = None
    ruta_vtt: Optional[str] = None
    titulo_generado: Optional[str] = None
    formato: Optional[str] = None
    score: float
    fecha: datetime
