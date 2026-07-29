"""Schemas para el editor de video básico."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AudioMode = Literal["mix", "replace", "keep"]


class EditAssetInfo(BaseModel):
    id: str
    kind: str  # video | audio
    filename: str
    original_name: str
    size_bytes: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    stream_url: str


class EditRenderRequest(BaseModel):
    video_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=12,
        description="Videos en orden (se pegan uno tras otro)",
    )
    audio_id: Optional[str] = Field(
        default=None,
        description="Audio opcional para mezclar o reemplazar",
    )
    start: float = Field(default=0.0, ge=0.0)
    end: Optional[float] = Field(
        default=None,
        ge=0.1,
        description="Fin del recorte en segundos (None = hasta el final)",
    )
    mirror: bool = False
    video_volume: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Volumen del audio del video (0–2)",
    )
    audio_volume: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Volumen del audio externo (0–2)",
    )
    audio_mode: AudioMode = Field(
        default="mix",
        description="mix | replace | keep (ignora audio externo)",
    )


class EditJobStart(BaseModel):
    job_id: str


class EditJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    filename: Optional[str] = None
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    duration: Optional[float] = None
    size_bytes: Optional[int] = None
