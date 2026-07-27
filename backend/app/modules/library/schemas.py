"""Schemas de biblioteca."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LibraryVideoItem(BaseModel):
    id: int
    nombre_original: str
    duracion: Optional[float] = None
    estado: str
    progreso: int = 0
    fecha_subida: datetime
    clips_count: int = 0

    model_config = {"from_attributes": True}


class LibraryClipItem(BaseModel):
    id: int
    video_id: int
    titulo_generado: Optional[str] = None
    duracion: float
    score: float
    formato: Optional[str] = None
    ruta_clip: str
    ruta_miniatura: Optional[str] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class LibraryResponse(BaseModel):
    videos: List[LibraryVideoItem] = []
    clips: List[LibraryClipItem] = []
