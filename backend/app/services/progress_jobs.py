"""Almacén en memoria de jobs de progreso (YouTube, etc.)."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProgressJob:
    id: str
    kind: str  # youtube | upload
    status: str = "pending"  # pending | running | completed | failed
    progress: int = 0
    detail: str = "En cola…"
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    video_id: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "detail": self.detail,
            "eta_seconds": self.eta_seconds,
            "error": self.error,
            "video_id": self.video_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.meta,
        }


class ProgressJobStore:
    """Singleton thread-safe para jobs de corta duración."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, ProgressJob] = {}

    def create(self, kind: str, detail: str = "Iniciando…", **meta: Any) -> ProgressJob:
        job = ProgressJob(
            id=uuid.uuid4().hex,
            kind=kind,
            status="pending",
            detail=detail,
            meta=dict(meta),
        )
        with self._lock:
            self._jobs[job.id] = job
            self._cleanup_locked()
        return job

    def get(self, job_id: str) -> Optional[ProgressJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        detail: Optional[str] = None,
        eta_seconds: Optional[int] = None,
        error: Optional[str] = None,
        video_id: Optional[int] = None,
        clear_eta: bool = False,
        **meta: Any,
    ) -> Optional[ProgressJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0, min(100, int(progress)))
            if detail is not None:
                job.detail = detail
            if clear_eta:
                job.eta_seconds = None
            elif eta_seconds is not None:
                job.eta_seconds = max(0, int(eta_seconds))
            if error is not None:
                job.error = error
            if video_id is not None:
                job.video_id = video_id
            if meta:
                job.meta.update(meta)
            job.updated_at = time.time()
            return job

    def _cleanup_locked(self) -> None:
        """Elimina jobs terminados de más de 1 hora."""
        now = time.time()
        stale = [
            jid
            for jid, j in self._jobs.items()
            if now - j.updated_at > 3600 and j.status in ("completed", "failed")
        ]
        for jid in stale:
            del self._jobs[jid]


progress_jobs = ProgressJobStore()
