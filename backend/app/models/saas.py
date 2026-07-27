"""Modelos SaaS de la segunda capa ClipAI (proyectos, contenido, créditos, etc.)."""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    SHORTS = "shorts"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    X = "x"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class Project(Base):
    """Proyecto de organización de videos/clips."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Caption(Base):
    """Metadatos opcionales de subtítulos por clip."""

    __tablename__ = "captions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estilo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    idioma: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Thumbnail(Base):
    """Miniatura asociada a un clip."""

    __tablename__ = "thumbnails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ruta: Mapped[str] = mapped_column(Text, nullable=False)
    texto_overlay: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClipContent(Base):
    """Contenido AI generado para un clip (títulos, descripciones, hashtags)."""

    __tablename__ = "clip_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    titles: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    descriptions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    hashtags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    cta: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    seo_keywords: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SocialAccount(Base):
    """Cuenta social conectada (stub OAuth)."""

    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    handle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ScheduledPost(Base):
    """Publicación programada o borrador."""

    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="SET NULL"), nullable=True, index=True
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus), default=PostStatus.DRAFT, nullable=False, index=True
    )
    titulo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsSnapshot(Base):
    """Snapshot de métricas (mock o reales)."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="SET NULL"), nullable=True, index=True
    )
    video_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    platform: Mapped[Optional[Platform]] = mapped_column(Enum(Platform), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class Plan(Base):
    """Plan de suscripción con créditos mensuales."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    credits_monthly: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    features: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Subscription(Base):
    """Suscripción de usuario a un plan."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CreditLedger(Base):
    """Movimiento de créditos (gasto/recarga)."""

    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Notification(Base):
    """Notificación in-app."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Job(Base):
    """Trabajo en cola en segundo plano."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TrendReport(Base):
    """Informe de tendencia por categoría/país."""

    __tablename__ = "trend_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(8), default="GLOBAL", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningInsight(Base):
    """Insight de aprendizaje a partir de analytics/clips."""

    __tablename__ = "learning_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clip_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clips.id", ondelete="SET NULL"), nullable=True
    )
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AutomationSettings(Base):
    """Flags de automatización post-proceso."""

    __tablename__ = "automation_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enrich_after_process: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_schedule_stubs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_thumbnails: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_platforms: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
