"""Schemas de miniaturas."""

from typing import Optional

from pydantic import BaseModel


class ThumbnailCreate(BaseModel):
    clip_id: int
    texto_overlay: Optional[str] = None
    at_seconds: Optional[float] = None


class ThumbnailRead(BaseModel):
    id: int
    clip_id: int
    ruta: str
    texto_overlay: Optional[str] = None
    es_principal: bool = True

    model_config = {"from_attributes": True}
