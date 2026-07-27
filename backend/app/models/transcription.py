"""Modelo de transcripción Whisper."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.video import Video


class Transcription(Base):
    __tablename__ = "transcripciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    idioma: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    segmentos: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    video: Mapped["Video"] = relationship("Video", back_populates="transcripciones")
