"""Schemas del editor de metadatos de clip."""

from typing import Optional

from pydantic import BaseModel, Field


class ClipEditorUpdate(BaseModel):
    titulo_generado: Optional[str] = Field(None, max_length=512)
    caption_texto: Optional[str] = None
    caption_estilo: Optional[str] = None
    caption_idioma: Optional[str] = None


class ClipEditorRead(BaseModel):
    clip_id: int
    titulo_generado: Optional[str] = None
    inicio: float
    fin: float
    duracion: float
    formato: Optional[str] = None
    ruta_clip: str
    ruta_miniatura: Optional[str] = None
    caption_texto: Optional[str] = None
    caption_estilo: Optional[str] = None
    caption_idioma: Optional[str] = None
