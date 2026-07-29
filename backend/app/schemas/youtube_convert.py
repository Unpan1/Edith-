"""Schemas: convertir YouTube a MP4 / MP3."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ConvertFormat = Literal["mp4", "mp3", "both"]


class YoutubeConvertRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    format: ConvertFormat = Field(
        default="both",
        description="mp4 | mp3 | both",
    )


class YoutubeConvertJobStart(BaseModel):
    job_id: str


class YoutubeConvertFile(BaseModel):
    kind: str  # mp4 | mp3
    filename: str
    size_bytes: int
    stream_url: str
    download_url: str
    display_name: Optional[str] = None


class YoutubeConvertJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    files: List[YoutubeConvertFile] = Field(default_factory=list)
