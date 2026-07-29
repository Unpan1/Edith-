"""Schemas para el módulo Voces (TTS)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class VoiceInfo(BaseModel):
    id: str
    name: str
    locale: str
    gender: str
    style: str


class SpeechMoodInfo(BaseModel):
    id: str
    label: str
    rate: str
    pitch: str


class VoiceListResponse(BaseModel):
    voices: List[VoiceInfo]
    moods: List[SpeechMoodInfo] = Field(default_factory=list)
    note: str = (
        "Voces gratis vía edge-tts. Los modos cambian ritmo, tono y volumen "
        "(sin leer código)."
    )


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    voice_id: str = Field(default="es-MX-DaliaNeural", max_length=80)
    rate: Optional[str] = Field(
        default=None,
        description="Opcional. Si se omite, usa el rate del mood. Ej: -10%, +15%",
    )
    pitch: Optional[str] = Field(
        default=None,
        description="Opcional. Si se omite, usa el pitch del mood. Ej: -5Hz, +5Hz",
    )
    mood: str = Field(default="neutral", description="Modo de habla")
    speed: int = Field(
        default=0,
        ge=-50,
        le=100,
        description="Ajuste de velocidad relativo al mood (-50 lento … +100 rápido)",
    )


class DialogueTurn(BaseModel):
    voice_id: str = Field(..., max_length=80)
    text: str = Field(..., min_length=1, max_length=3000)
    mood: str = Field(default="neutral")
    character: Optional[str] = Field(default=None, max_length=60)
    rate: Optional[str] = None
    speed: Optional[int] = Field(default=None, ge=-50, le=100)


class VoiceDialogueRequest(BaseModel):
    turns: List[DialogueTurn] = Field(..., min_length=1, max_length=40)
    pause_ms: int = Field(default=350, ge=80, le=2000)
    speed: int = Field(default=0, ge=-50, le=100)


class VoicePreviewRequest(BaseModel):
    voice_id: str = Field(default="es-MX-DaliaNeural", max_length=80)
    mood: str = Field(default="neutral")
    speed: int = Field(default=0, ge=-50, le=100)
    text: Optional[str] = Field(
        default=None,
        max_length=280,
        description="Texto corto de prueba. Si se omite, usa una frase de ejemplo.",
    )


class VoiceSynthesizeResponse(BaseModel):
    voice_id: str
    filename: str
    size_bytes: int
    stream_url: str
    download_url: str
    mood: str = "neutral"
    message: str = "Narración generada"
    rate: Optional[str] = None
    speed: int = 0



class VoiceJobStart(BaseModel):
    job_id: str


class VoiceJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    detail: str
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    voice_id: Optional[str] = None
    filename: Optional[str] = None
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    mood: Optional[str] = None
    size_bytes: Optional[int] = None
    message: Optional[str] = None

