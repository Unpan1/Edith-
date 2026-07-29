"""Rutas: videos narrados desde historias."""

from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.config.settings import Settings, get_settings
from app.schemas.stories import (
    StoryGenerateRequest,
    StoryJobStart,
    StoryJobStatus,
    StoryOptionsResponse,
    StoryPresetInfo,
)
from app.services.progress_jobs import progress_jobs
from app.services.story_video_service import FORMAT_SIZES, StoryVideoService
from app.utils.exceptions import AppError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stories", tags=["stories"])


def get_story_service(settings: Settings = Depends(get_settings)) -> StoryVideoService:
    return StoryVideoService(settings)


@router.get("/options", response_model=StoryOptionsResponse)
def story_options(service: StoryVideoService = Depends(get_story_service)):
    return StoryOptionsResponse(
        presets=[StoryPresetInfo(**p) for p in service.list_presets()],
        formats=list(FORMAT_SIZES.keys()),
        note=(
            "Pega tu historia, elige un tipo de video e instrucciones. "
            "Se genera un MP4 narrado (escenas + voz + visuales). Sin APIs de pago."
        ),
    )


def _run_story(job_id: str, payload: dict) -> None:
    from app.utils.exceptions import AppError as _AppError
    from app.utils.exceptions import JobCancelledError

    try:
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id, status="running", progress=2, detail="Preparando historia…"
        )
        body = StoryGenerateRequest.model_validate(payload)
        service = StoryVideoService(get_settings())

        def on_progress(pct: int, detail: str, eta: Optional[int]) -> None:
            if progress_jobs.is_cancelled(job_id):
                return
            progress_jobs.update(
                job_id,
                status="running",
                progress=pct,
                detail=detail,
                eta_seconds=eta,
                clear_eta=eta is None,
            )

        result = service.generate(
            story=body.story,
            preset=body.preset,
            instructions=body.instructions,
            format=body.format,
            voice_id=body.voice_id,
            mood=body.mood,
            language=body.language,
            on_progress=on_progress,
            should_cancel=lambda: progress_jobs.is_cancelled(job_id),
        )
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail="Video listo",
            clear_eta=True,
            filename=result.filename,
            stream_url=f"/stories/video/{result.filename}",
            download_url=f"/stories/video/{result.filename}?download=1",
            scenes_count=result.scenes_count,
            duration_seconds=result.duration_seconds,
            preset=result.preset,
            format=result.format,
        )
    except JobCancelledError:
        progress_jobs.update(
            job_id,
            status="cancelled",
            detail="Generación cancelada",
            clear_eta=True,
        )
        logger.info("Story job %s cancelado", job_id)
    except Exception as exc:  # noqa: BLE001
        if progress_jobs.is_cancelled(job_id):
            progress_jobs.update(
                job_id,
                status="cancelled",
                detail="Generación cancelada",
                clear_eta=True,
            )
            return
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("Story job %s: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error al generar el video",
            error=msg[:500],
            clear_eta=True,
        )


@router.post("/generate", response_model=StoryJobStart, status_code=202)
def start_story_generate(body: StoryGenerateRequest):
    job = progress_jobs.create(
        "story",
        detail="En cola…",
        preset=body.preset,
        format=body.format,
    )
    threading.Thread(
        target=_run_story,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"story-{job.id[:8]}",
    ).start()
    return StoryJobStart(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=StoryJobStatus)
def story_job_status(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "story":
        raise AppError("Job de historia no encontrado", status_code=404)
    meta = job.meta or {}
    return StoryJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        filename=meta.get("filename"),
        stream_url=meta.get("stream_url"),
        download_url=meta.get("download_url"),
        scenes_count=meta.get("scenes_count"),
        duration_seconds=meta.get("duration_seconds"),
        preset=meta.get("preset"),
        format=meta.get("format"),
    )


@router.post("/jobs/{job_id}/cancel", response_model=StoryJobStatus)
def cancel_story_job(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "story":
        raise AppError("Job de historia no encontrado", status_code=404)
    if job.status in ("completed", "failed"):
        raise AppError("El job ya terminó y no se puede cancelar", status_code=400)
    updated = progress_jobs.request_cancel(job_id)
    if not updated:
        raise AppError("Job de historia no encontrado", status_code=404)
    return StoryJobStatus(
        job_id=updated.id,
        status=updated.status,
        progress=updated.progress,
        detail=updated.detail or "Cancelado",
        eta_seconds=None,
        error=None,
    )


@router.get("/video/{filename}")
def stream_story_video(
    filename: str,
    download: int = 0,
    service: StoryVideoService = Depends(get_story_service),
):
    path = service.resolve_file(filename)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name if download else None,
        headers=headers,
    )
