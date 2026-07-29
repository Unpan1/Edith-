"""Schemas para composición manual (split arriba/abajo)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.clip import ClipRead
from app.schemas.options import ClipFormat


class CropBoxNorm(BaseModel):
    """Recorte normalizado 0–1 relativo al frame del video fuente."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def fits_frame(self):
        if self.x + self.w > 1.001 or self.y + self.h > 1.001:
            raise ValueError("El recorte sale del frame (x+w y y+h deben ser ≤ 1)")
        return self


class ComposeSplitRequest(BaseModel):
    video_id: int
    format: ClipFormat = ClipFormat.VERTICAL_9_16
    start: float = Field(default=0.0, ge=0.0)
    end: Optional[float] = Field(default=None, gt=0.0)
    top: CropBoxNorm
    bottom: CropBoxNorm
    mirror_horizontal: bool = False
    title: Optional[str] = Field(default=None, max_length=200)


class ComposeJobStart(BaseModel):
    job_id: str
    message: str = "Composición iniciada"


class ComposeJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    clip_id: Optional[int] = None
    clip: Optional[ClipRead] = None


class VideoSourceInfo(BaseModel):
    id: int
    nombre_original: str
    duracion: Optional[float] = None
    width: int
    height: int
    stream_url: str
