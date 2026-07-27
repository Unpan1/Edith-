"""Schemas Pydantic para usuarios."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: EmailStr
    fecha_creacion: datetime
