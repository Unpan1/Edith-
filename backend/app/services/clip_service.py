"""Servicio de generación de clips a partir de highlights."""

import time
from pathlib import Path
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.ai.highlight_detector import HighlightCandidate
from app.ai.whisper_service import WhisperSegment
from app.models.clip import Clip
from app.schemas.options import FORMAT_RESOLUTIONS, ProcessOptions
from app.storage.storage_service import StorageService
from app.subtitle.subtitle_service import SubtitleService
from app.utils.logger import get_logger
from app.video.face_tracker import ActiveSegment, SpeakerRegions
from app.video.ffmpeg_service import FFmpegService
from app.video.layout_service import LayoutService

logger = get_logger(__name__)


class ClipService:
    """Genera archivos de clip, subtítulos incrustados y miniaturas."""

    def __init__(
        self,
        ffmpeg: FFmpegService,
        subtitle: SubtitleService,
        storage: StorageService,
        layout: LayoutService,
    ):
        self.ffmpeg = ffmpeg
        self.subtitle = subtitle
        self.storage = storage
        self.layout = layout

    def generate_clips(
        self,
        db: Session,
        *,
        video_id: int,
        video_path: Path,
        highlights: Sequence[HighlightCandidate],
        segments: Sequence[WhisperSegment],
        options: ProcessOptions,
        regions: Optional[SpeakerRegions] = None,
        activity: Optional[Sequence[ActiveSegment]] = None,
        on_progress=None,
    ) -> List[Clip]:
        out_dir = self.storage.clip_dir(video_id)
        created: List[Clip] = []
        formats = options.formats
        total = max(1, len(highlights) * len(formats))
        done = 0
        start_all = time.perf_counter()

        for idx, hl in enumerate(highlights):
            for fmt in formats:
                t0 = time.perf_counter()
                base = f"clip_{idx + 1}_{fmt.value}_{int(hl.start)}_{int(hl.end)}"
                laid_out = out_dir / f"{base}_layout.mp4"
                final_path = out_dir / f"{base}.mp4"
                thumb_path = out_dir / f"{base}.jpg"

                logger.info(
                    "Clip %d/%d fmt=%s [%.1f–%.1f] score=%.2f",
                    done + 1, total, fmt.value, hl.start, hl.end, hl.score,
                )

                # 1. Corte + layout (vertical split / smart crop / etc.)
                self.layout.render_clip(
                    video_path,
                    laid_out,
                    start=hl.start,
                    end=hl.end,
                    fmt=fmt,
                    options=options,
                    regions=regions,
                    activity=activity,
                )

                # 2. Subtítulos (SRT/VTT/ASS)
                srt_path = vtt_path = ass_path = None
                if options.export_srt or options.export_vtt or options.burn_subtitles:
                    play_res = FORMAT_RESOLUTIONS.get(fmt, (1080, 1920))
                    srt_path, vtt_path, ass_path = self.subtitle.generate_for_clip(
                        segments,
                        hl.start,
                        hl.end,
                        out_dir,
                        base,
                        style=options.subtitle_style,
                        position=options.subtitle_position,
                        font_size=options.subtitle_size,
                        play_res=play_res,
                    )
                    if not options.export_srt and srt_path:
                        srt_path.unlink(missing_ok=True)
                        srt_path = None
                    if not options.export_vtt and vtt_path:
                        vtt_path.unlink(missing_ok=True)
                        vtt_path = None

                # 3. Burn-in con ASS (estilos limpios / karaoke)
                if options.burn_subtitles:
                    burn_file = ass_path if ass_path and ass_path.exists() else srt_path
                    if burn_file and Path(burn_file).exists():
                        try:
                            self.ffmpeg.burn_subtitles(
                                laid_out,
                                burn_file,
                                final_path,
                                style_name=options.subtitle_style.value,
                                use_ass=burn_file.suffix.lower() == ".ass",
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Burn-in falló (%s). Usando clip sin subtítulos.", exc)
                            laid_out.replace(final_path)
                    else:
                        laid_out.replace(final_path)
                else:
                    laid_out.replace(final_path)

                if laid_out.exists() and laid_out != final_path:
                    laid_out.unlink(missing_ok=True)

                # 4. Miniatura
                mid = max(0.0, (hl.end - hl.start) / 2)
                try:
                    self.ffmpeg.extract_thumbnail(final_path, thumb_path, at_seconds=min(mid, 2.0))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Miniatura fallida: %s", exc)
                    thumb_path = None  # type: ignore

                clip = Clip(
                    video_id=video_id,
                    inicio=hl.start,
                    fin=hl.end,
                    duracion=hl.duration,
                    ruta_clip=str(final_path),
                    ruta_miniatura=str(thumb_path) if thumb_path else None,
                    ruta_srt=str(srt_path) if srt_path else None,
                    ruta_vtt=str(vtt_path) if vtt_path else None,
                    titulo_generado=hl.title,
                    formato=fmt.value,
                    score=hl.score,
                )
                db.add(clip)
                db.flush()
                created.append(clip)

                done += 1
                logger.info("Clip generado en %.2fs → %s", time.perf_counter() - t0, final_path)
                if on_progress:
                    pct = 60 + int((done / total) * 35)
                    detail = (
                        f"Clip {done}/{total}: {hl.title or f'parte {idx + 1}'} "
                        f"({fmt.value.replace('_', ' ')})"
                    )
                    try:
                        on_progress(pct, detail)
                    except TypeError:
                        on_progress(pct)

        db.commit()
        for c in created:
            db.refresh(c)

        logger.info(
            "Generados %d clips en %.2fs para video %d",
            len(created),
            time.perf_counter() - start_all,
            video_id,
        )
        return created

    def get_clip(self, db: Session, clip_id: int) -> Clip | None:
        return db.get(Clip, clip_id)

    def list_by_video(self, db: Session, video_id: int) -> List[Clip]:
        return (
            db.query(Clip)
            .filter(Clip.video_id == video_id)
            .order_by(Clip.score.desc())
            .all()
        )
