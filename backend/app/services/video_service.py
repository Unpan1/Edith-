"""Servicio orquestador del ciclo de vida de videos."""

import shutil
import time
from pathlib import Path
from typing import BinaryIO, List, Optional

from sqlalchemy.orm import Session

from app.ai.highlight_detector import HighlightDetector
from app.ai.whisper_service import WhisperService
from app.config.settings import Settings
from app.models.clip import Clip
from app.models.transcription import Transcription
from app.models.video import Video, VideoStatus
from app.schemas.options import ProcessOptions
from app.services.clip_service import ClipService
from app.storage.storage_service import StorageService
from app.utils.exceptions import CorruptVideoError, ProcessingError, VideoNotFoundError
from app.utils.logger import get_logger
from app.utils.validators import validate_file_size, validate_video_extension
from app.schemas.options import ProcessingMode
from app.video.ffmpeg_service import FFmpegService
from app.video.layout_service import LayoutService
from app.video.video_splitter import build_full_video_segments
from app.video.youtube_service import YoutubeService

logger = get_logger(__name__)


class VideoService:
    """
    Orquesta: upload → audio → Whisper → highlights → layout → clips → subtítulos.
    """

    def __init__(
        self,
        settings: Settings,
        storage: StorageService,
        ffmpeg: FFmpegService,
        whisper: WhisperService,
        highlight_detector: HighlightDetector,
        clip_service: ClipService,
        layout: LayoutService,
    ):
        self.settings = settings
        self.storage = storage
        self.ffmpeg = ffmpeg
        self.whisper = whisper
        self.highlight_detector = highlight_detector
        self.clip_service = clip_service
        self.layout = layout
        self.youtube = YoutubeService(settings)

    def upload(
        self,
        db: Session,
        file_obj: BinaryIO,
        filename: str,
        size_bytes: int,
    ) -> Video:
        ext = validate_video_extension(filename, self.settings)
        validate_file_size(size_bytes, self.settings)

        path = self.storage.save_upload(file_obj, filename, ext)

        try:
            duration, _w, _h = self.ffmpeg.get_video_info(path)
        except CorruptVideoError:
            self.storage.delete_path(path)
            raise
        except Exception as exc:  # noqa: BLE001
            self.storage.delete_path(path)
            raise CorruptVideoError(str(exc)) from exc

        video = Video(
            nombre_original=filename,
            ruta_archivo=str(path),
            duracion=duration,
            tamano=size_bytes,
            estado=VideoStatus.UPLOADED,
            progreso=0,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        logger.info(
            "Video #%d subido: %s (%.1fs, %.1f MB)",
            video.id, filename, duration, size_bytes / (1024 * 1024),
        )
        return video

    def import_from_youtube(
        self,
        db: Session,
        url: str,
        on_progress=None,
    ) -> Video:
        """Descarga un video público de YouTube (yt-dlp, gratis) y lo registra."""
        result = self.youtube.download(
            url,
            self.storage.upload_dir,
            on_progress=on_progress,
        )

        # Renombrar a UUID como el resto de uploads
        ext = result.path.suffix.lower() or ".mp4"
        final_name = self.storage.generate_uuid_name(ext)
        final_path = self.storage.upload_dir / final_name
        try:
            result.path.replace(final_path)
        except OSError:
            shutil.move(str(result.path), str(final_path))

        if on_progress:
            on_progress(98, "Registrando video en la biblioteca…", 2)

        try:
            duration, _w, _h = self.ffmpeg.get_video_info(final_path)
        except Exception as exc:  # noqa: BLE001
            self.storage.delete_path(final_path)
            raise CorruptVideoError(str(exc)) from exc

        if result.duration and (not duration or duration <= 0):
            duration = result.duration

        video = Video(
            nombre_original=result.title,
            ruta_archivo=str(final_path.resolve()),
            duracion=duration,
            tamano=result.size_bytes,
            estado=VideoStatus.UPLOADED,
            progreso=100,
            progreso_detalle="Importación completada",
            eta_segundos=None,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        logger.info(
            "Video #%d importado de YouTube: %s (%.1fs, %.1f MB)",
            video.id,
            result.title,
            duration or 0,
            result.size_bytes / (1024 * 1024),
        )
        return video

    def list_videos(self, db: Session) -> List[Video]:
        return db.query(Video).order_by(Video.fecha_subida.desc()).all()

    def get_video(self, db: Session, video_id: int) -> Video:
        video = db.get(Video, video_id)
        if not video:
            raise VideoNotFoundError(video_id)
        return video

    def get_clips(self, db: Session, video_id: int) -> List[Clip]:
        self.get_video(db, video_id)
        return self.clip_service.list_by_video(db, video_id)

    def delete_video(self, db: Session, video_id: int) -> None:
        video = self.get_video(db, video_id)
        ruta = video.ruta_archivo
        db.delete(video)
        db.commit()
        self.storage.delete_video_assets(ruta, video_id)
        logger.info("Video #%d eliminado", video_id)

    def save_options(self, db: Session, video_id: int, options: ProcessOptions) -> Video:
        video = self.get_video(db, video_id)
        video.opciones = options.model_dump(mode="json")
        db.add(video)
        db.commit()
        db.refresh(video)
        return video

    def process(
        self,
        db: Session,
        video_id: int,
        options: Optional[ProcessOptions] = None,
    ) -> Video:
        video = self.get_video(db, video_id)
        opts = options or (
            ProcessOptions.model_validate(video.opciones)
            if video.opciones
            else ProcessOptions()
        )
        video.opciones = opts.model_dump(mode="json")
        db.add(video)
        db.commit()

        start_all = time.perf_counter()
        audio_path: Optional[Path] = None
        duration = float(video.duracion or 0)

        def stage_eta(remaining_weight: float) -> int:
            """ETA heurístico según duración del video y peso restante del pipeline."""
            # Whisper base ~0.3–0.6x realtime en CPU; clips ~pocos s por segmento
            base = max(20.0, duration * 0.45 + 25.0)
            elapsed = time.perf_counter() - start_all
            est_total = base
            remaining = max(0.0, est_total * remaining_weight - elapsed * 0.15)
            return max(5, int(remaining))

        try:
            for existing in list(video.clips):
                db.delete(existing)
            for existing in list(video.transcripciones):
                db.delete(existing)
            db.commit()

            self._set_status(
                db, video, VideoStatus.EXTRACTING_AUDIO, 8,
                detail="Extrayendo pista de audio…",
                eta_seconds=stage_eta(0.95),
            )
            audio_path = self.storage.get_temp_path(".wav")
            self.ffmpeg.extract_audio(video.ruta_archivo, audio_path)

            self._set_status(
                db, video, VideoStatus.TRANSCRIBING, 20,
                detail="Transcribiendo con Whisper (puede tardar)…",
                eta_seconds=stage_eta(0.75),
            )
            transcription_result = self.whisper.transcribe(
                audio_path, language=opts.language
            )

            transcription = Transcription(
                video_id=video.id,
                texto=transcription_result.text,
                idioma=transcription_result.language,
                segmentos=transcription_result.segments_as_dicts(),
            )
            db.add(transcription)
            db.commit()

            self._set_status(
                db, video, VideoStatus.ANALYZING, 48,
                detail="Detectando momentos del video…",
                eta_seconds=stage_eta(0.45),
            )

            # Primero highlights/split (rápido); luego rostros con tope de muestras
            if opts.processing_mode == ProcessingMode.FULL_SPLIT:
                duration = video.duracion or 0.0
                if duration <= 0:
                    duration, _, _ = self.ffmpeg.get_video_info(video.ruta_archivo)
                highlights = build_full_video_segments(duration, opts)
                if not highlights:
                    raise ProcessingError(
                        "No se pudo dividir el video. Verifica la duración."
                    )
                logger.info(
                    "Modo full_split: %d partes (duración total %.1fs)",
                    len(highlights),
                    duration,
                )
                analyze_detail = f"Video dividido en {len(highlights)} partes"
            else:
                highlights = self.highlight_detector.detect(
                    transcription_result.segments,
                    min_duration=opts.min_clip_duration,
                    max_duration=opts.max_clip_duration,
                    max_clips=opts.max_clips,
                )
                if not highlights:
                    raise ProcessingError(
                        "No se detectaron momentos destacados. "
                        "El video puede ser demasiado corto o sin habla."
                    )
                analyze_detail = f"Detectados {len(highlights)} momentos destacados"

            def face_progress(msg: str) -> None:
                self._set_status(
                    db, video, VideoStatus.ANALYZING, 52,
                    detail=msg,
                    eta_seconds=stage_eta(0.40),
                )

            self._set_status(
                db, video, VideoStatus.ANALYZING, 50,
                detail=f"{analyze_detail}. Analizando rostros…",
                eta_seconds=stage_eta(0.42),
            )
            regions, activity = self.layout.analyze_speakers(
                Path(video.ruta_archivo), opts, on_progress=face_progress
            )

            self._set_status(
                db, video, VideoStatus.GENERATING_CLIPS, 55,
                detail=f"{analyze_detail}. Generando clips…",
                eta_seconds=stage_eta(0.35),
            )

            def on_progress(pct: int, detail: Optional[str] = None) -> None:
                status = (
                    VideoStatus.ADDING_SUBTITLES
                    if opts.burn_subtitles and pct >= 75
                    else VideoStatus.GENERATING_CLIPS
                )
                # ETA proporcional al % restante de esta fase (55→95)
                rem = max(0.05, (95 - pct) / 40.0)
                self._set_status(
                    db, video, status, pct,
                    detail=detail or (
                        "Incrustando subtítulos…"
                        if status == VideoStatus.ADDING_SUBTITLES
                        else "Renderizando clips…"
                    ),
                    eta_seconds=stage_eta(rem * 0.35),
                )

            self.clip_service.generate_clips(
                db,
                video_id=video.id,
                video_path=Path(video.ruta_archivo),
                highlights=highlights,
                segments=transcription_result.segments,
                options=opts,
                regions=regions,
                activity=activity,
                on_progress=on_progress,
            )

            # Hook segunda capa SaaS (único punto de extensión post-clips)
            try:
                self._set_status(
                    db, video, VideoStatus.ADDING_SUBTITLES, 96,
                    detail="Enriqueciendo títulos y miniaturas…",
                    eta_seconds=5,
                )
                from app.modules.content_ai.enrichment import ContentEnrichmentService
                from app.modules.deps import DEFAULT_USER_ID

                ContentEnrichmentService().enrich_video_clips(
                    db, video.id, user_id=DEFAULT_USER_ID
                )
            except Exception as enrich_exc:  # noqa: BLE001
                logger.warning(
                    "Enrichment post-clips video #%d: %s",
                    video_id,
                    enrich_exc,
                )

            self._set_status(
                db, video, VideoStatus.COMPLETED, 100,
                detail="Proceso completado",
                eta_seconds=None,
            )
            logger.info(
                "Pipeline video #%d completado en %.2fs (modo=%s formats=%s)",
                video_id,
                time.perf_counter() - start_all,
                opts.content_mode.value,
                [f.value for f in opts.formats],
            )
            db.refresh(video)
            return video

        except Exception as exc:  # noqa: BLE001
            logger.exception("Error procesando video #%d: %s", video_id, exc)
            self._set_status(
                db, video, VideoStatus.FAILED, video.progreso or 0,
                error=str(exc),
                detail="Error en el procesamiento",
                eta_seconds=None,
            )
            raise
        finally:
            if audio_path:
                self.storage.delete_path(audio_path)

    def _set_status(
        self,
        db: Session,
        video: Video,
        status: VideoStatus,
        progress: int,
        error: Optional[str] = None,
        detail: Optional[str] = None,
        eta_seconds: Optional[int] = None,
    ) -> None:
        video.estado = status
        video.progreso = max(0, min(100, progress))
        video.mensaje_error = error
        if detail is not None:
            video.progreso_detalle = detail
        if status in (VideoStatus.COMPLETED, VideoStatus.FAILED, VideoStatus.UPLOADED):
            video.eta_segundos = None
        elif eta_seconds is not None:
            video.eta_segundos = max(0, int(eta_seconds))
        db.add(video)
        db.commit()
        db.refresh(video)
        logger.info(
            "Video #%d → %s (%d%%)%s%s",
            video.id,
            status.value,
            progress,
            f" | {detail}" if detail else "",
            f" | {error}" if error else "",
        )
