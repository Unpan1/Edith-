"""Rutas del módulo Composición (separado del pipeline de clips IA)."""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db
from app.schemas.clip import ClipRead
from app.schemas.compose import (
    ComposeJobStart,
    ComposeJobStatus,
    ComposeSplitRequest,
    VideoSourceInfo,
)
from app.services.clip_service import ClipService
from app.services.compose_service import ComposeService
from app.services.dependencies import (
    get_clip_service,
    get_ffmpeg_service,
    get_storage_service,
    get_video_service,
)
from app.services.progress_jobs import progress_jobs
from app.services.video_service import VideoService
from app.utils.exceptions import AppError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/compose", tags=["compose"])


def get_compose_service() -> ComposeService:
    return ComposeService(get_ffmpeg_service(), get_storage_service())


def _run_compose(job_id: str, payload: dict) -> None:
    from app.utils.exceptions import AppError as _AppError

    db = SessionLocal()
    try:
        progress_jobs.update(job_id, status="running", progress=2, detail="Preparando composición…")
        req = ComposeSplitRequest.model_validate(payload)

        def on_progress(pct: int, detail: str) -> None:
            progress_jobs.update(
                job_id,
                status="running",
                progress=pct,
                detail=detail,
            )

        service = get_compose_service()
        clip = service.render_split(db, req, on_progress=on_progress)
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail="Composición lista",
            video_id=clip.video_id,
            clear_eta=True,
        )
        job = progress_jobs.get(job_id)
        if job:
            job.meta["clip_id"] = clip.id
    except Exception as exc:  # noqa: BLE001
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("Compose job %s falló: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error en composición",
            error=msg[:500],
            clear_eta=True,
        )
    finally:
        db.close()


@router.get("/videos/{video_id}/source", response_model=VideoSourceInfo)
def compose_source_info(
    video_id: int,
    db: Session = Depends(get_db),
    videos: VideoService = Depends(get_video_service),
    compose: ComposeService = Depends(get_compose_service),
):
    video = videos.get_video(db, video_id)
    w, h, dur = compose.get_source_size(video)
    return VideoSourceInfo(
        id=video.id,
        nombre_original=video.nombre_original,
        duracion=video.duracion or dur,
        width=w,
        height=h,
        stream_url=f"/compose/videos/{video.id}/stream",
    )


@router.get("/videos/{video_id}/stream")
def compose_stream_video(
    video_id: int,
    db: Session = Depends(get_db),
    videos: VideoService = Depends(get_video_service),
):
    video = videos.get_video(db, video_id)
    path = Path(video.ruta_archivo)
    if not path.exists():
        raise AppError("Archivo de video no encontrado", status_code=404)
    suffix = path.suffix.lower()
    media = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
    }.get(suffix, "video/mp4")
    return FileResponse(path, media_type=media, filename=path.name)


@router.post("/split", response_model=ComposeJobStart, status_code=202)
def compose_split_start(body: ComposeSplitRequest):
    """Exporta un split manual arriba/abajo (job en segundo plano)."""
    job = progress_jobs.create("compose", detail="En cola…", video_id=body.video_id)
    threading.Thread(
        target=_run_compose,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"compose-{job.id[:8]}",
    ).start()
    return ComposeJobStart(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=ComposeJobStatus)
def compose_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    clips: ClipService = Depends(get_clip_service),
):
    job = progress_jobs.get(job_id)
    if not job:
        raise AppError("Job de composición no encontrado", status_code=404)

    clip_id = job.meta.get("clip_id")
    clip_read = None
    if clip_id:
        clip = clips.get_clip(db, int(clip_id))
        if clip:
            clip_read = clip

    return ComposeJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        clip_id=int(clip_id) if clip_id else None,
        clip=clip_read,
    )
