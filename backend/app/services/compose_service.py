"""Composición manual: apilar dos recortes elegidos por el usuario."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.video import Video
from app.schemas.compose import ComposeSplitRequest, CropBoxNorm
from app.schemas.options import FORMAT_RESOLUTIONS
from app.storage.storage_service import StorageService
from app.utils.exceptions import ProcessingError, VideoNotFoundError
from app.utils.logger import get_logger
from app.video.ffmpeg_service import FFmpegService

logger = get_logger(__name__)


def _norm_to_pixels(
    box: CropBoxNorm, src_w: int, src_h: int, panel_ar: float
) -> Tuple[int, int, int, int]:
    """
    Convierte caja normalizada a crop FFmpeg (x,y,w,h) en píxeles pares.
    Ajusta el crop al AR del panel de salida para evitar deformar.
    """
    # Región pedida por el usuario
    rx = max(0, int(box.x * src_w))
    ry = max(0, int(box.y * src_h))
    rw = max(2, int(box.w * src_w))
    rh = max(2, int(box.h * src_h))

    # Forzar AR del panel (cover dentro de la caja elegida)
    region_ar = rw / max(rh, 1)
    if region_ar > panel_ar:
        # Región más ancha → recortar anchos
        new_w = max(2, int(rh * panel_ar))
        rx = rx + max(0, (rw - new_w) // 2)
        rw = new_w
    else:
        new_h = max(2, int(rw / panel_ar))
        ry = ry + max(0, (rh - new_h) // 2)
        rh = new_h

    # Clamp al frame
    rw = min(rw, src_w - rx)
    rh = min(rh, src_h - ry)
    rw -= rw % 2
    rh -= rh % 2
    rx -= rx % 2
    ry -= ry % 2
    rw = max(2, rw)
    rh = max(2, rh)
    if rx + rw > src_w:
        rx = max(0, src_w - rw)
    if ry + rh > src_h:
        ry = max(0, src_h - rh)
    return rx, ry, rw, rh


class ComposeService:
    def __init__(self, ffmpeg: FFmpegService, storage: StorageService):
        self.ffmpeg = ffmpeg
        self.storage = storage

    def get_source_size(self, video: Video) -> Tuple[int, int, float]:
        duration, w, h = self.ffmpeg.get_video_info(video.ruta_archivo)
        return w, h, duration

    def render_split(
        self,
        db: Session,
        req: ComposeSplitRequest,
        *,
        on_progress=None,
    ) -> Clip:
        video = db.get(Video, req.video_id)
        if not video:
            raise VideoNotFoundError(req.video_id)

        if on_progress:
            on_progress(5, "Leyendo video fuente…")

        src_w, src_h, full_dur = self.get_source_size(video)
        start = max(0.0, req.start)
        end = float(req.end) if req.end is not None else float(video.duracion or full_dur)
        end = min(end, full_dur)
        if end - start < 0.5:
            raise ProcessingError("El tramo debe durar al menos 0.5 segundos")

        out_w, out_h = FORMAT_RESOLUTIONS[req.format]
        half_h = out_h // 2
        panel_ar = out_w / max(half_h, 1)

        top_px = _norm_to_pixels(req.top, src_w, src_h, panel_ar)
        bot_px = _norm_to_pixels(req.bottom, src_w, src_h, panel_ar)

        if on_progress:
            on_progress(20, f"Renderizando split {req.format.value}…")

        out_dir = self.storage.clip_dir(video.id)
        base = f"compose_split_{int(start)}_{int(end)}_{req.format.value}"
        out_path = out_dir / f"{base}.mp4"
        thumb_path = out_dir / f"{base}.jpg"

        self.ffmpeg.cut_interview_stack(
            Path(video.ruta_archivo),
            out_path,
            start=start,
            end=end,
            out_w=out_w,
            half_h=half_h - (half_h % 2),
            top_box=top_px,
            bottom_box=bot_px,
            mirror_horizontal=req.mirror_horizontal,
        )

        if on_progress:
            on_progress(85, "Generando miniatura…")

        try:
            self.ffmpeg.extract_thumbnail(out_path, thumb_path, at_seconds=min(1.0, (end - start) / 2))
            thumb = str(thumb_path)
        except Exception:  # noqa: BLE001
            thumb = None

        title = (req.title or f"Composición split · {req.format.value}").strip()
        clip = Clip(
            video_id=video.id,
            inicio=start,
            fin=end,
            duracion=end - start,
            ruta_clip=str(out_path),
            ruta_miniatura=thumb,
            ruta_srt=None,
            ruta_vtt=None,
            titulo_generado=title,
            formato=req.format.value,
            score=0.0,
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)

        if on_progress:
            on_progress(100, "Composición lista")

        logger.info(
            "Compose split video #%d → clip #%d top=%s bot=%s",
            video.id,
            clip.id,
            top_px,
            bot_px,
        )
        return clip
