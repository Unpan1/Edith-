"""Schemas Pydantic para videos."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.video import VideoStatus
from app.schemas.clip import ClipRead
from app.schemas.options import ProcessOptions


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_original: str
    ruta_archivo: str
    duracion: Optional[float] = None
    tamano: Optional[int] = None
    estado: VideoStatus
    progreso: int = 0
    mensaje_error: Optional[str] = None
    progreso_detalle: Optional[str] = None
    eta_segundos: Optional[int] = None
    opciones: Optional[Any] = None
    fecha_subida: datetime
    clips: List[ClipRead] = Field(default_factory=list)


class VideoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_original: str
    duracion: Optional[float] = None
    tamano: Optional[int] = None
    estado: VideoStatus
    progreso: int = 0
    mensaje_error: Optional[str] = None
    progreso_detalle: Optional[str] = None
    eta_segundos: Optional[int] = None
    opciones: Optional[Any] = None
    fecha_subida: datetime


class ProcessResponse(BaseModel):
    video_id: int
    message: str
    estado: VideoStatus
    opciones: Optional[ProcessOptions] = None


class YoutubeImportRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500, description="URL de YouTube")


class YoutubeJobStart(BaseModel):
    job_id: str
    message: str = "Descarga iniciada"


class YoutubeJobStatus(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    video_id: Optional[int] = None
    video: Optional[VideoRead] = None
