"""Servicio de miniaturas con FFmpeg."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.clip import Clip
from app.models.saas import Thumbnail
from app.services.dependencies import get_ffmpeg_service
from app.utils.exceptions import ClipNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ThumbnailService:
    """Extrae y registra miniaturas de clips."""

    def ensure_thumbnail(
        self,
        db: Session,
        clip_id: int,
        texto_overlay: Optional[str] = None,
        at_seconds: Optional[float] = None,
    ) -> Thumbnail:
        clip = db.get(Clip, clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        settings = get_settings()
        ffmpeg = get_ffmpeg_service()
        out_dir = Path(settings.output_folder) / "thumbnails"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"clip_{clip_id}_thumb.jpg"

        from app.models.video import Video

        video = db.get(Video, clip.video_id)
        video_file = video.ruta_archivo if video else None

        if at_seconds is None:
            source = clip.ruta_clip if clip.ruta_clip else None
            if source and Path(source).exists():
                video_path = source
                seek = max(0.5, (clip.duracion or 2.0) / 2.0)
            else:
                video_path = video_file
                seek = clip.inicio + 0.5
        else:
            if clip.ruta_clip and Path(clip.ruta_clip).exists():
                video_path = clip.ruta_clip
                seek = at_seconds
            else:
                video_path = video_file
                seek = clip.inicio + at_seconds

        if not video_path:
            raise ClipNotFoundError(clip_id)

        ffmpeg.extract_thumbnail(video_path, out_path, at_seconds=seek)

        if texto_overlay:
            overlay_path = out_dir / f"clip_{clip_id}_thumb_text.jpg"
            try:
                ffmpeg.burn_thumbnail_text(out_path, overlay_path, texto_overlay)
                out_path = overlay_path
            except Exception as exc:  # noqa: BLE001
                logger.warning("Overlay de texto falló: %s", exc)

        # marcar otras como no principales
        for old in db.query(Thumbnail).filter(Thumbnail.clip_id == clip_id).all():
            old.es_principal = False
            db.add(old)

        row = Thumbnail(
            clip_id=clip_id,
            ruta=str(out_path),
            texto_overlay=texto_overlay,
            es_principal=True,
        )
        db.add(row)

        if not clip.ruta_miniatura:
            clip.ruta_miniatura = str(out_path)
            db.add(clip)

        db.commit()
        db.refresh(row)
        return row

    def list_for_clip(self, db: Session, clip_id: int) -> List[Thumbnail]:
        return (
            db.query(Thumbnail)
            .filter(Thumbnail.clip_id == clip_id)
            .order_by(Thumbnail.fecha.desc())
            .all()
        )
