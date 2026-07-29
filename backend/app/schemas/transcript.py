"""Schemas para extracción de texto de YouTube."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptCueRead(BaseModel):
    start: float
    end: float
    text: str
    speaker: int = 1


class YoutubeTranscriptRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    language: Optional[str] = Field(default="es", max_length=10)
    prefer_whisper: bool = False
    detect_speakers: bool = True


class YoutubeTranscriptJobStart(BaseModel):
    job_id: str
    message: str = "Extracción iniciada"


class YoutubeTranscriptResultRead(BaseModel):
    title: str
    url: str
    language: Optional[str] = None
    source: str
    text: str
    duration: Optional[float] = None
    speakers_count: int = 1
    cues: List[TranscriptCueRead] = Field(default_factory=list)


class YoutubeTranscriptJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    result: Optional[YoutubeTranscriptResultRead] = None
