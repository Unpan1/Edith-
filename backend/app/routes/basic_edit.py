"""Rutas: editor de video básico."""

from __future__ import annotations

import threading
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.config.settings import Settings, get_settings
from app.schemas.basic_edit import (
    EditAssetInfo,
    EditJobStart,
    EditJobStatus,
    EditRenderRequest,
)
from app.services.basic_edit_service import BasicEditService
from app.services.progress_jobs import progress_jobs
from app.utils.exceptions import AppError, JobCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/edit", tags=["edit"])


def get_edit_service(settings: Settings = Depends(get_settings)) -> BasicEditService:
    return BasicEditService(settings)


def _asset_info(a) -> EditAssetInfo:
    return EditAssetInfo(
        id=a.id,
        kind=a.kind,
        filename=a.path.name,
        original_name=a.original_name,
        size_bytes=a.size_bytes,
        duration=a.duration,
        width=a.width,
        height=a.height,
        stream_url=f"/edit/assets/{a.id}/stream",
    )


@router.post("/upload", response_model=EditAssetInfo)
async def upload_edit_asset(
    file: UploadFile = File(...),
    kind: str = Form(default="auto"),
    service: BasicEditService = Depends(get_edit_service),
):
    data = await file.read()
    asset = service.save_upload(
        filename=file.filename or "file.bin",
        data=data,
        kind_hint=kind or "auto",
    )
    return _asset_info(asset)


@router.get("/assets", response_model=list[EditAssetInfo])
def list_edit_assets(service: BasicEditService = Depends(get_edit_service)):
    return [_asset_info(a) for a in service.list_assets()]


@router.get("/assets/{asset_id}/stream")
def stream_edit_asset(
    asset_id: str,
    service: BasicEditService = Depends(get_edit_service),
):
    asset = service.get_asset(asset_id)
    media = "audio/mpeg" if asset.kind == "audio" else "video/mp4"
    if asset.path.suffix.lower() == ".wav":
        media = "audio/wav"
    elif asset.path.suffix.lower() in (".m4a", ".aac"):
        media = "audio/mp4"
    return FileResponse(asset.path, media_type=media)


def _run_render(job_id: str, payload: dict) -> None:
    from app.utils.exceptions import AppError as _AppError

    try:
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id, status="running", progress=2, detail="Preparando edición…"
        )
        body = EditRenderRequest.model_validate(payload)
        service = BasicEditService(get_settings())

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

        result = service.render(
            video_ids=body.video_ids,
            audio_id=body.audio_id,
            start=body.start,
            end=body.end,
            mirror=body.mirror,
            video_volume=body.video_volume,
            audio_volume=body.audio_volume,
            audio_mode=body.audio_mode,
            on_progress=on_progress,
            should_cancel=lambda: progress_jobs.is_cancelled(job_id),
        )
        if progress_jobs.is_cancelled(job_id):
            return
        progress_jobs.update(
            job_id,
            status="completed",
            progress=100,
            detail="Edición lista",
            clear_eta=True,
            filename=result.filename,
            stream_url=f"/edit/files/{result.filename}",
            download_url=f"/edit/files/{result.filename}?download=1",
            duration=result.duration,
            size_bytes=result.size_bytes,
        )
    except JobCancelledError:
        progress_jobs.update(
            job_id, status="cancelled", detail="Edición cancelada", clear_eta=True
        )
    except Exception as exc:  # noqa: BLE001
        if progress_jobs.is_cancelled(job_id):
            progress_jobs.update(
                job_id, status="cancelled", detail="Edición cancelada", clear_eta=True
            )
            return
        msg = exc.message if isinstance(exc, _AppError) else str(exc)
        logger.exception("Edit job %s: %s", job_id, msg)
        progress_jobs.update(
            job_id,
            status="failed",
            detail="Error al editar",
            error=msg[:500],
            clear_eta=True,
        )


@router.post("/render", response_model=EditJobStart, status_code=202)
def start_edit_render(body: EditRenderRequest):
    job = progress_jobs.create("edit", detail="En cola…", videos=len(body.video_ids))
    threading.Thread(
        target=_run_render,
        args=(job.id, body.model_dump(mode="json")),
        daemon=True,
        name=f"edit-{job.id[:8]}",
    ).start()
    return EditJobStart(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=EditJobStatus)
def edit_job_status(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "edit":
        raise AppError("Job de edición no encontrado", status_code=404)
    meta = job.meta or {}
    return EditJobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        detail=job.detail,
        eta_seconds=job.eta_seconds,
        error=job.error,
        filename=meta.get("filename"),
        stream_url=meta.get("stream_url"),
        download_url=meta.get("download_url"),
        duration=meta.get("duration"),
        size_bytes=meta.get("size_bytes"),
    )


@router.post("/jobs/{job_id}/cancel", response_model=EditJobStatus)
def cancel_edit_job(job_id: str):
    job = progress_jobs.get(job_id)
    if not job or job.kind != "edit":
        raise AppError("Job de edición no encontrado", status_code=404)
    if job.status in ("completed", "failed"):
        raise AppError("El job ya terminó", status_code=400)
    updated = progress_jobs.request_cancel(job_id)
    if not updated:
        raise AppError("Job de edición no encontrado", status_code=404)
    return EditJobStatus(
        job_id=updated.id,
        status=updated.status,
        progress=updated.progress,
        detail=updated.detail or "Cancelado",
    )


@router.get("/files/{filename}")
def stream_edit_file(
    filename: str,
    download: int = 0,
    service: BasicEditService = Depends(get_edit_service),
):
    path = service.resolve_output(filename)
    headers = {}
    if download:
        ascii_name = path.name
        headers["Content-Disposition"] = (
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(ascii_name)}"
        )
    return FileResponse(path, media_type="video/mp4", headers=headers)
