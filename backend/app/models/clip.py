"""Modelo de clip generado."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.video import Video


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inicio: Mapped[float] = mapped_column(Float, nullable=False)
    fin: Mapped[float] = mapped_column(Float, nullable=False)
    duracion: Mapped[float] = mapped_column(Float, nullable=False)
    ruta_clip: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_miniatura: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ruta_srt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ruta_vtt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    titulo_generado: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    formato: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    video: Mapped["Video"] = relationship("Video", back_populates="clips")
