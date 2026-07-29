"""Rutas: convertir YouTube a MP4 / MP3."""

from __future__ import annotations

import re
import threading
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.config.settings import Settings, get_settings
from app.schemas.youtube_convert import (
    YoutubeConvertFile,
    YoutubeConvertJobStart,
    YoutubeConvertJobStatus,
    YoutubeConvertRequest,
)
from app.services.progress_jobs import progress_jobs
from app.services.youtube_convert_service import YoutubeConvertService
from app.utils.exceptions import AppError, JobCancelledError
from app.utils.logger import get_logger
from app.video.youtube_service import YoutubeService

logger = get_logger(__name__)

router = APIRouter(prefix="/convert", tags=["convert"])


def get_convert_service(
    settings: Settings = Depends(get_settings),
) -> YoutubeConvertService:
    return YoutubeConvertService(settings)


def _run_convert(job_id: str, payload: dict) -> None:
    from app.utils.exceptions import AppError as _AppError

    try:
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id, status="running", progress=2, detail="Preparando conversión…"
        )
        body = YoutubeConvertRequest.model_validate(payload)
        service = YoutubeConvertService(get_settings())

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

        result = service.convert(
            body.url,
            fmt=body.format,
            on_progress=on_progress,
            should_cancel=lambda: progress_jobs.is_cancelled(job_id),
        )
        if progress_jobs.is_cancelled(job_id):
            return

        files = [
            {
                "kind": f.kind,
                "filename": f.filename,
                "size_bytes": f.size_bytes,
                "stream_url": f"/convert/files/{f.filename}",
                "download_url": f"/convert/files/{f.filename}?download=1",
                "display_name": f.display_name or f.filename,
            }
            for f in result.files
        ]
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail="Conversión lista",
            clear_eta=True,
            title=result.title,
            duration=result.duration,
            format=result.format,
            files=files,
        )
    except JobCancelledError:
        progress_jobs.update(
            job_id,
            status="cancelled",
            detail="Conversión cancelada",
            clear_eta=True,
        )
        logger.info("Convert job %s cancelado", job_id)
    except Exception as exc:  # noqa: BLE001
        if progress_jobs.is_cancelled(job_id):
            progress_jobs.update(
                job_id,
                status="cancelled",
                detail="Conversión cancelada",
                clear_eta=True,
            )
            return
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("Convert job %s: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error al convertir",
            error=msg[:500],
            clear_eta=True,
        )


@router.post("/youtube", response_model=YoutubeConvertJobStart, status_code=202)
def start_youtube_convert(body: YoutubeConvertRequest):
    YoutubeService(get_settings()).normalize_url(body.url)
    job = progress_jobs.create(
        "convert",
        detail="En cola…",
        format=body.format,
        url=body.url[:200],
    )
    threading.Thread(
        target=_run_convert,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"convert-{job.id[:8]}",
    ).start()
    return YoutubeConvertJobStart(job_id=job.id)


@router.get("/youtube/jobs/{job_id}", response_model=YoutubeConvertJobStatus)
def convert_job_status(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "convert":
        raise AppError("Job de conversión no encontrado", status_code=404)
    meta = job.meta or {}
    files = [YoutubeConvertFile(**f) for f in (meta.get("files") or [])]
    return YoutubeConvertJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        title=meta.get("title"),
        duration=meta.get("duration"),
        format=meta.get("format"),
        files=files,
    )


@router.post("/youtube/jobs/{job_id}/cancel", response_model=YoutubeConvertJobStatus)
def cancel_convert_job(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "convert":
        raise AppError("Job de conversión no encontrado", status_code=404)
    if job.status in ("completed", "failed"):
        raise AppError("El job ya terminó y no se puede cancelar", status_code=400)
    updated = progress_jobs.request_cancel(job_id)
    if not updated:
        raise AppError("Job de conversión no encontrado", status_code=404)
    return YoutubeConvertJobStatus(
        job_id=updated.id,
        status=updated.status,
        progress=updated.progress,
        detail=updated.detail or "Cancelado",
        eta_seconds=None,
        error=None,
        files=[],
    )


@router.get("/files/{filename}")
def stream_convert_file(
    filename: str,
    download: int = 0,
    service: YoutubeConvertService = Depends(get_convert_service),
):
    from urllib.parse import quote

    path = service.resolve_file(filename)
    media = "audio/mpeg" if path.suffix.lower() == ".mp3" else "video/mp4"
    # Nombre ASCII seguro: evita 500 de Starlette con emojis/espacios
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.name) or f"youtube{path.suffix}"
    headers = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(path.name)}"
        )
    return FileResponse(
        path,
        media_type=media,
        headers=headers,
    )
