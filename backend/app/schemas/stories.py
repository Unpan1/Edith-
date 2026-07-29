"""Schemas para generación de videos desde historias."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

StoryPreset = Literal[
    "narracion",
    "misterio",
    "motivacional",
    "terror",
    "documental",
    "humor",
]
StoryFormat = Literal["9:16", "16:9", "1:1"]


class StoryGenerateRequest(BaseModel):
    story: str = Field(..., min_length=20, max_length=20000)
    preset: StoryPreset = "narracion"
    instructions: str = Field(
        default="",
        max_length=1000,
        description="Tipo de video / instrucciones libres",
    )
    format: StoryFormat = "9:16"
    voice_id: str = Field(default="es-MX-DaliaNeural", max_length=80)
    mood: str = Field(default="neutral", max_length=40)
    language: str = Field(default="es", max_length=8)


class StoryJobStart(BaseModel):
    job_id: str


class StorySceneInfo(BaseModel):
    index: int
    text: str
    caption: str


class StoryJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    filename: Optional[str] = None
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    scenes_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    preset: Optional[str] = None
    format: Optional[str] = None


class StoryPresetInfo(BaseModel):
    id: str
    label: str
    description: str


class StoryOptionsResponse(BaseModel):
    presets: List[StoryPresetInfo]
    formats: List[str]
    note: str
