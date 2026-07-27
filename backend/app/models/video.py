"""Modelo de video subido."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.clip import Clip
    from app.models.transcription import Transcription


class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    GENERATING_CLIPS = "generating_clips"
    ADDING_SUBTITLES = "adding_subtitles"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_original: Mapped[str] = mapped_column(String(512), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    duracion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tamano: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estado: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus),
        default=VideoStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    progreso: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mensaje_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progreso_detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eta_segundos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opciones: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    fecha_subida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transcripciones: Mapped[List["Transcription"]] = relationship(
        "Transcription",
        back_populates="video",
        cascade="all, delete-orphan",
    )
    clips: Mapped[List["Clip"]] = relationship(
        "Clip",
        back_populates="video",
        cascade="all, delete-orphan",
    )
