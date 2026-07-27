"""Schemas de contenido AI."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ContentGenerateRequest(BaseModel):
    clip_id: int


class ClipContentRead(BaseModel):
    id: int
    clip_id: int
    titles: List[str] = Field(default_factory=list)
    descriptions: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    seo_keywords: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}
