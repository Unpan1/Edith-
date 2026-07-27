"""Schemas de proyectos."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None


class ProjectUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class ProjectRead(BaseModel):
    id: int
    user_id: int
    nombre: str
    descripcion: Optional[str] = None
    fecha_creacion: datetime

    model_config = {"from_attributes": True}
