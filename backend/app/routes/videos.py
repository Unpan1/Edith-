"""Endpoints de videos y clips."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db
from app.models.video import VideoStatus
from app.schemas.clip import ClipRead
from app.schemas.options import ProcessOptions
from app.schemas.video import (
    ProcessResponse,
    VideoListItem,
    VideoRead,
    YoutubeImportRequest,
    YoutubeJobStart,
    YoutubeJobStatus,
)
from app.services.clip_service import ClipService
from app.services.dependencies import get_clip_service, get_video_service
from app.services.progress_jobs import progress_jobs
from app.services.video_service import VideoService
from app.utils.exceptions import AppError, ClipNotFoundError, InvalidFileError
from app.utils.logger import get_logger
from app.video.youtube_service import YoutubeService

logger = get_logger(__name__)

router = APIRouter(tags=["videos"])


def _run_processing(video_id: int, options_dict: Optional[dict] = None) -> None:
    from app.services.dependencies import get_video_service as _get_vs

    db = SessionLocal()
    try:
        service = _get_vs()
        opts = ProcessOptions.model_validate(options_dict) if options_dict else None
        service.process(db, video_id, opts)
    except Exception:  # noqa: BLE001
        logger.exception("Background processing falló para video #%d", video_id)
    finally:
        db.close()


def _run_youtube_import(job_id: str, url: str) -> None:
    from app.services.dependencies import get_video_service as _get_vs
    from app.utils.exceptions import AppError as _AppError

    db = SessionLocal()
    try:
        progress_jobs.update(
            job_id,
            status="running",
            progress=1,
            detail="Preparando descarga de YouTube…",
        )

        def on_progress(pct: int, detail: str, eta: Optional[int]) -> None:
            progress_jobs.update(
                job_id,
                status="running",
                progress=pct,
                detail=detail,
                eta_seconds=eta,
                clear_eta=eta is None,
            )

        service = _get_vs()
        # Validar URL pronto
        YoutubeService(service.settings).normalize_url(url)
        video = service.import_from_youtube(db, url, on_progress=on_progress)
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail="Importación completada",
            video_id=video.id,
            clear_eta=True,
        )
    except Exception as exc:  # noqa: BLE001
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("YouTube import job %s falló: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error al importar",
            error=msg[:500],
            clear_eta=True,
        )
    finally:
        db.close()


@router.post("/upload", response_model=VideoRead, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    if not file.filename:
        raise InvalidFileError("Nombre de archivo vacío")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    video = service.upload(db, file.file, file.filename, size)
    return video


@router.post("/upload/youtube", response_model=YoutubeJobStart, status_code=202)
def upload_from_youtube(
    body: YoutubeImportRequest,
    service: VideoService = Depends(get_video_service),
):
    """Inicia descarga de YouTube en segundo plano (progreso vía /upload/youtube/jobs/{id})."""
    import threading

    YoutubeService(service.settings).normalize_url(body.url)
    job = progress_jobs.create(
        "youtube",
        detail="En cola para descargar…",
        url=body.url[:200],
    )
    threading.Thread(
        target=_run_youtube_import,
        args=(job.id, body.url),
        daemon=True,
        name=f"yt-{job.id[:8]}",
    ).start()
    return YoutubeJobStart(job_id=job.id, message="Descarga iniciada")


@router.get("/upload/youtube/jobs/{job_id}", response_model=YoutubeJobStatus)
def youtube_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    job = progress_jobs.get(job_id)
    if not job:
        raise AppError("Job de descarga no encontrado", status_code=404)

    video_read = None
    if job.video_id:
        try:
            video_read = service.get_video(db, job.video_id)
        except Exception:  # noqa: BLE001
            video_read = None

    return YoutubeJobStatus(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        video_id=job.video_id,
        video=video_read,
    )


@router.get("/videos", response_model=List[VideoListItem])
def list_videos(
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    return service.list_videos(db)


@router.get("/videos/{video_id}", response_model=VideoRead)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    return service.get_video(db, video_id)


@router.get("/options/defaults", response_model=ProcessOptions)
def default_options():
    """Opciones por defecto para la UI."""
    return ProcessOptions()


@router.post("/videos/{video_id}/process", response_model=ProcessResponse)
def process_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    options: ProcessOptions = Body(default_factory=ProcessOptions),
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    video = service.get_video(db, video_id)

    if video.estado in (
        VideoStatus.EXTRACTING_AUDIO,
        VideoStatus.TRANSCRIBING,
        VideoStatus.ANALYZING,
        VideoStatus.GENERATING_CLIPS,
        VideoStatus.ADDING_SUBTITLES,
    ):
        return ProcessResponse(
            video_id=video.id,
            message="El video ya se está procesando",
            estado=video.estado,
            opciones=ProcessOptions.model_validate(video.opciones) if video.opciones else options,
        )

    service.save_options(db, video_id, options)

    video.estado = VideoStatus.EXTRACTING_AUDIO
    video.progreso = 5
    video.mensaje_error = None
    video.progreso_detalle = "Iniciando procesamiento…"
    video.eta_segundos = None
    db.add(video)
    db.commit()
    db.refresh(video)

    background_tasks.add_task(_run_processing, video_id, options.model_dump(mode="json"))
    logger.info(
        "Procesamiento encolado video #%d modo=%s formats=%s",
        video_id,
        options.content_mode.value,
        [f.value for f in options.formats],
    )

    return ProcessResponse(
        video_id=video.id,
        message="Procesamiento iniciado",
        estado=video.estado,
        opciones=options,
    )


@router.get("/videos/{video_id}/clips", response_model=List[ClipRead])
def list_clips(
    video_id: int,
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    return service.get_clips(db, video_id)


@router.get("/clip/{clip_id}", response_model=ClipRead)
def get_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    clip_service: ClipService = Depends(get_clip_service),
):
    clip = clip_service.get_clip(db, clip_id)
    if not clip:
        raise ClipNotFoundError(clip_id)
    return clip


@router.get("/clip/{clip_id}/download")
def download_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    clip_service: ClipService = Depends(get_clip_service),
):
    clip = clip_service.get_clip(db, clip_id)
    if not clip:
        raise ClipNotFoundError(clip_id)
    path = Path(clip.ruta_clip)
    if not path.exists():
        raise AppError("Archivo de clip no encontrado en disco", status_code=404)
    filename = f"{clip.titulo_generado or f'clip_{clip.id}'}.mp4"
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
    return FileResponse(path, media_type="video/mp4", filename=safe)


@router.get("/clip/{clip_id}/stream")
def stream_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    clip_service: ClipService = Depends(get_clip_service),
):
    clip = clip_service.get_clip(db, clip_id)
    if not clip:
        raise ClipNotFoundError(clip_id)
    path = Path(clip.ruta_clip)
    if not path.exists():
        raise AppError("Archivo de clip no encontrado en disco", status_code=404)
    return FileResponse(path, media_type="video/mp4")


@router.get("/clip/{clip_id}/thumbnail")
def clip_thumbnail(
    clip_id: int,
    db: Session = Depends(get_db),
    clip_service: ClipService = Depends(get_clip_service),
):
    clip = clip_service.get_clip(db, clip_id)
    if not clip or not clip.ruta_miniatura:
        raise AppError("Miniatura no disponible", status_code=404)
    path = Path(clip.ruta_miniatura)
    if not path.exists():
        raise AppError("Miniatura no encontrada", status_code=404)
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/video/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    service: VideoService = Depends(get_video_service),
):
    service.delete_video(db, video_id)
    return None
