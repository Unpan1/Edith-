"""Rutas del módulo Voces (TTS gratis con edge-tts)."""

from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.config.settings import Settings, get_settings
from app.schemas.voices import (
    SpeechMoodInfo,
    VoiceDialogueRequest,
    VoiceInfo,
    VoiceJobStart,
    VoiceJobStatus,
    VoiceListResponse,
    VoicePreviewRequest,
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
)
from app.services.progress_jobs import progress_jobs
from app.services.voice_service import VoiceService
from app.utils.exceptions import AppError, JobCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/voices", tags=["voices"])


def get_voice_service(settings: Settings = Depends(get_settings)) -> VoiceService:
    return VoiceService(settings)


def _job_to_status(job) -> VoiceJobStatus:
    meta = job.meta or {}
    return VoiceJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        voice_id=meta.get("voice_id"),
        filename=meta.get("filename"),
        stream_url=meta.get("stream_url"),
        download_url=meta.get("download_url"),
        mood=meta.get("mood"),
        size_bytes=meta.get("size_bytes"),
        message=meta.get("message"),
    )


@router.get("", response_model=VoiceListResponse)
def list_voices(service: VoiceService = Depends(get_voice_service)):
    voices = [VoiceInfo(**v) for v in service.list_voices()]
    moods = [SpeechMoodInfo(**m) for m in service.list_moods()]
    return VoiceListResponse(voices=voices, moods=moods)


def _complete_voice_job(job_id: str, result, message: str) -> None:
    if progress_jobs.is_cancelled(job_id):
        return
    progress_jobs.update(
        job_id,
        status="completed",
        progress=100,
        detail=message,
        clear_eta=True,
        voice_id=result.voice_id,
        filename=result.filename,
        stream_url=f"/voices/audio/{result.filename}",
        download_url=f"/voices/audio/{result.filename}?download=1",
        mood=result.mood,
        size_bytes=result.size_bytes,
        message=message,
    )


def _fail_or_cancel(job_id: str, exc: Exception) -> None:
    from app.utils.exceptions import AppError as _AppError

    if isinstance(exc, JobCancelledError) or progress_jobs.is_cancelled(job_id):
        progress_jobs.update(
            job_id,
            status="cancelled",
            detail="Generación cancelada",
            clear_eta=True,
        )
        logger.info("Voice job %s cancelado", job_id)
        return
    msg = exc.message if isinstance(exc, _AppError) else str(exc)
    logger.exception("Voice job %s: %s", job_id, msg)
    progress_jobs.update(
        job_id,
        status="failed",
        detail="Error al generar la voz",
        error=msg[:500],
        clear_eta=True,
    )


def _run_synthesize(job_id: str, payload: dict) -> None:
    try:
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id, status="running", progress=5, detail="Generando narración…"
        )
        body = VoiceSynthesizeRequest.model_validate(payload)
        service = VoiceService(get_settings())
        result = service.synthesize(
            text=body.text,
            voice_id=body.voice_id,
            rate=body.rate,
            pitch=body.pitch,
            mood=body.mood,
            speed=body.speed,
            should_cancel=lambda: progress_jobs.is_cancelled(job_id),
        )
        _complete_voice_job(job_id, result, "Narración generada")
    except Exception as exc:  # noqa: BLE001
        _fail_or_cancel(job_id, exc)


def _run_dialogue(job_id: str, payload: dict) -> None:
    try:
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id, status="running", progress=3, detail="Preparando diálogo…"
        )
        body = VoiceDialogueRequest.model_validate(payload)
        service = VoiceService(get_settings())
        turns = [t.model_dump() for t in body.turns]

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

        result = service.synthesize_dialogue(
            turns,
            pause_ms=body.pause_ms,
            speed=body.speed,
            should_cancel=lambda: progress_jobs.is_cancelled(job_id),
            on_progress=on_progress,
        )
        _complete_voice_job(
            job_id, result, f"Diálogo con {len(body.turns)} turnos generado"
        )
    except Exception as exc:  # noqa: BLE001
        _fail_or_cancel(job_id, exc)


PREVIEW_SAMPLES = {
    "es": (
        "Hola, soy el narrador. Así suena mi voz a esta velocidad. "
        "Úsala para probar antes de generar todo tu texto."
    ),
    "en": (
        "Hello, I am the narrator. This is how I sound at this speed. "
        "Use this preview before generating your full text."
    ),
}


@router.post("/preview", response_model=VoiceSynthesizeResponse)
def preview_voice(
    body: VoicePreviewRequest,
    service: VoiceService = Depends(get_voice_service),
):
    """Vista previa rápida (frase corta) para probar voz, modo y velocidad."""
    sample = (body.text or "").strip()
    if not sample:
        voice = body.voice_id or ""
        lang = "en" if voice.startswith("en-") else "es"
        sample = PREVIEW_SAMPLES[lang]
    result = service.synthesize(
        text=sample,
        voice_id=body.voice_id,
        mood=body.mood,
        speed=body.speed,
    )
    mood_params = service._mood_params(body.mood, speed=body.speed)
    return VoiceSynthesizeResponse(
        voice_id=result.voice_id,
        filename=result.filename,
        size_bytes=result.size_bytes,
        stream_url=f"/voices/audio/{result.filename}",
        download_url=f"/voices/audio/{result.filename}?download=1",
        mood=result.mood,
        message="Vista previa lista",
        rate=str(mood_params.get("rate") or "+0%"),
        speed=body.speed,
    )


@router.post("/synthesize", response_model=VoiceJobStart, status_code=202)
def synthesize_voice(body: VoiceSynthesizeRequest):
    job = progress_jobs.create("voice", detail="En cola…", mode="single")
    threading.Thread(
        target=_run_synthesize,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"voice-{job.id[:8]}",
    ).start()
    return VoiceJobStart(job_id=job.id)


@router.post("/dialogue", response_model=VoiceJobStart, status_code=202)
def synthesize_dialogue(body: VoiceDialogueRequest):
    """Genera un audio único con varios personajes / voces."""
    job = progress_jobs.create(
        "voice", detail="En cola…", mode="dialogue", turns=len(body.turns)
    )
    threading.Thread(
        target=_run_dialogue,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"voice-dlg-{job.id[:8]}",
    ).start()
    return VoiceJobStart(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=VoiceJobStatus)
def voice_job_status(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "voice":
        raise AppError("Job de voz no encontrado", status_code=404)
    return _job_to_status(job)


@router.post("/jobs/{job_id}/cancel", response_model=VoiceJobStatus)
def cancel_voice_job(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "voice":
        raise AppError("Job de voz no encontrado", status_code=404)
    if job.status in ("completed", "failed"):
        raise AppError("El job ya terminó y no se puede cancelar", status_code=400)
    updated = progress_jobs.request_cancel(job_id)
    if not updated:
        raise AppError("Job de voz no encontrado", status_code=404)
    return _job_to_status(updated)


@router.get("/audio/{filename}")
def stream_voice_audio(
    filename: str,
    download: int = 0,
    service: VoiceService = Depends(get_voice_service),
):
    path = service.resolve_file(filename)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=path.name if download else None,
        headers=headers,
    )
