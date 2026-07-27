"""Revisión inicial — crea users, videos, transcripciones, clips."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre_original", sa.String(length=512), nullable=False),
        sa.Column("ruta_archivo", sa.Text(), nullable=False),
        sa.Column("duracion", sa.Float(), nullable=True),
        sa.Column("tamano", sa.Integer(), nullable=True),
        sa.Column(
            "estado",
            sa.Enum(
                "uploaded",
                "extracting_audio",
                "transcribing",
                "analyzing",
                "generating_clips",
                "adding_subtitles",
                "completed",
                "failed",
                name="videostatus",
            ),
            nullable=False,
        ),
        sa.Column("progreso", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
        sa.Column("fecha_subida", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_estado", "videos", ["estado"], unique=False)

    op.create_table(
        "transcripciones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("idioma", sa.String(length=16), nullable=True),
        sa.Column("segmentos", mysql.JSON(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcripciones_video_id", "transcripciones", ["video_id"], unique=False)

    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.Float(), nullable=False),
        sa.Column("fin", sa.Float(), nullable=False),
        sa.Column("duracion", sa.Float(), nullable=False),
        sa.Column("ruta_clip", sa.Text(), nullable=False),
        sa.Column("ruta_miniatura", sa.Text(), nullable=True),
        sa.Column("ruta_srt", sa.Text(), nullable=True),
        sa.Column("ruta_vtt", sa.Text(), nullable=True),
        sa.Column("titulo_generado", sa.String(length=512), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clips_video_id", "clips", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_table("clips")
    op.drop_table("transcripciones")
    op.drop_table("videos")
    op.drop_table("users")
