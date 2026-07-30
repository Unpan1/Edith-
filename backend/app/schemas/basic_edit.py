"""Schemas para el editor de video con timeline."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AudioMode = Literal["mix", "replace", "keep"]
TimelineClipKind = Literal["video", "image", "audio", "title"]
ExportFormat = Literal["mp4", "webm", "mov", "mkv", "gif", "mp3", "wav"]


class EditAssetInfo(BaseModel):
    id: str
    kind: str  # video | audio | image
    filename: str
    original_name: str
    size_bytes: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    stream_url: str


class EditRenderRequest(BaseModel):
    """Legacy: concat + un audio. Preferir TimelineRenderRequest."""

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
    video_volume: float = Field(default=1.0, ge=0.0, le=2.0)
    audio_volume: float = Field(default=1.0, ge=0.0, le=2.0)
    audio_mode: AudioMode = Field(default="mix")


class TimelineClip(BaseModel):
    id: str
    kind: TimelineClipKind
    asset_id: Optional[str] = Field(
        default=None,
        description="Requerido para video/image/audio",
    )
    track: str = Field(description="V1 | T1 | A1 | A2 | …")
    start: float = Field(ge=0.0, description="Inicio en la timeline (s)")
    duration: float = Field(gt=0.05, le=600.0, description="Duración en timeline (s)")
    source_offset: float = Field(
        default=0.0,
        ge=0.0,
        description="Offset dentro del archivo fuente (tras un corte)",
    )
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    # Títulos
    text: Optional[str] = Field(default=None, max_length=200)
    font_family: str = Field(default="Arial", max_length=64)
    font_size: int = Field(default=48, ge=12, le=200)
    color: str = Field(default="white", max_length=32)
    x_percent: float = Field(default=50.0, ge=0.0, le=100.0)
    y_percent: float = Field(default=18.0, ge=0.0, le=100.0)


class TimelineRenderRequest(BaseModel):
    clips: List[TimelineClip] = Field(..., min_length=1, max_length=40)
    width: int = Field(default=1280, ge=320, le=1920)
    height: int = Field(default=720, ge=240, le=1920)
    mirror: bool = False
    export_format: ExportFormat = Field(
        default="mp4",
        description="mp4 | webm | mov | mkv | gif | mp3 | wav",
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
