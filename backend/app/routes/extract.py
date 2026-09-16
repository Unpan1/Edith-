"""Rutas: extracción de texto desde YouTube (módulo separado)."""

from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.schemas.transcript import (
    YoutubeTranscriptJobStart,
    YoutubeTranscriptJobStatus,
    YoutubeTranscriptRequest,
    YoutubeTranscriptResultRead,
    TranscriptCueRead,
)
from app.services.dependencies import get_ffmpeg_service, get_whisper_service
from app.services.progress_jobs import progress_jobs
from app.services.youtube_transcript_service import YoutubeTranscriptService
from app.utils.exceptions import AppError
from app.utils.logger import get_logger
from app.video.youtube_service import YoutubeService

logger = get_logger(__name__)

router = APIRouter(prefix="/extract", tags=["extract"])


def get_transcript_service(
    settings: Settings = Depends(get_settings),
) -> YoutubeTranscriptService:
    whisper = None
    ffmpeg = None
    try:
        whisper = get_whisper_service()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Whisper no disponible para extract: %s", exc)
    try:
        ffmpeg = get_ffmpeg_service()
    except Exception as exc:  # noqa: BLE001
        logger.warning("FFmpeg no disponible para extract: %s", exc)
    return YoutubeTranscriptService(settings, whisper=whisper, ffmpeg=ffmpeg)


def _run_extract(job_id: str, payload: dict) -> None:
    from app.utils.exceptions import AppError as _AppError

    try:
        progress_jobs.update(
            job_id, status="running", progress=2, detail="Preparando extracción…"
        )
        req = YoutubeTranscriptRequest.model_validate(payload)
        settings = get_settings()
        whisper = None
        ffmpeg = None
        try:
            whisper = get_whisper_service()
        except Exception:  # noqa: BLE001
            pass
        try:
            ffmpeg = get_ffmpeg_service()
        except Exception:  # noqa: BLE001
            pass
        service = YoutubeTranscriptService(settings, whisper=whisper, ffmpeg=ffmpeg)

        def on_progress(pct: int, detail: str, eta: Optional[int]) -> None:
            progress_jobs.update(
                job_id,
                status="running",
                progress=pct,
                detail=detail,
                eta_seconds=eta,
                clear_eta=eta is None,
            )

        result = service.extract(
            req.url,
            language=req.language,
            prefer_whisper=req.prefer_whisper,
            detect_speakers=req.detect_speakers,
            on_progress=on_progress,
        )
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail=f"Texto listo · {result.speakers_count} hablante(s)",
            clear_eta=True,
            title=result.title,
            source=result.source,
            language=result.language,
            text=result.text,
            url=result.url,
            duration=result.duration,
            speakers_count=result.speakers_count,
            platform=result.platform,
            cues=[
                {
                    "start": c.start,
                    "end": c.end,
                    "text": c.text,
                    "speaker": c.speaker,
                }
                for c in result.cues[:500]
            ],
        )
    except Exception as exc:  # noqa: BLE001
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("Extract job %s: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error al extraer texto",
            error=msg[:500],
            clear_eta=True,
        )


@router.post("/youtube", response_model=YoutubeTranscriptJobStart, status_code=202)
def start_youtube_extract(
    body: YoutubeTranscriptRequest,
    settings: Settings = Depends(get_settings),
):
    """Extrae texto de YouTube / Instagram / Facebook (subtítulos o Whisper)."""
    YoutubeService(settings).normalize_media_url(body.url)
    job = progress_jobs.create("extract", detail="En cola…", url=body.url[:200])
    threading.Thread(
        target=_run_extract,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"extract-{job.id[:8]}",
    ).start()
    return YoutubeTranscriptJobStart(job_id=job.id)


@router.get("/youtube/jobs/{job_id}", response_model=YoutubeTranscriptJobStatus)
def youtube_extract_status(job_id: str):
    job = progress_jobs.get(job_id)
    if not job:
        raise AppError("Job de extracción no encontrado", status_code=404)

    result = None
    if job.status == "completed" and job.meta.get("text") is not None:
        cues_raw = job.meta.get("cues") or []
        result = YoutubeTranscriptResultRead(
            title=str(job.meta.get("title") or "Video"),
            url=str(job.meta.get("url") or ""),
            language=job.meta.get("language"),
            source=str(job.meta.get("source") or "unknown"),
            text=str(job.meta.get("text") or ""),
            duration=job.meta.get("duration"),
            speakers_count=int(job.meta.get("speakers_count") or 1),
            platform=job.meta.get("platform"),
            cues=[TranscriptCueRead(**c) for c in cues_raw if isinstance(c, dict)],
        )

    return YoutubeTranscriptJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        result=result,
    )
