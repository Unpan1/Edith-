"""Cola de trabajos abstracta (in-memory; lista para Redis/RabbitMQ)."""

from __future__ import annotations

import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class QueueJob:
    """Representación en memoria de un job encolado."""

    id: str
    tipo: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "queued"
    attempts: int = 0
    max_attempts: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    user_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class JobQueue(ABC):
    """Interfaz de cola (implementable con Redis/RabbitMQ)."""

    @abstractmethod
    def enqueue(
        self,
        tipo: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        user_id: Optional[int] = None,
        max_attempts: int = 3,
    ) -> QueueJob:
        ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[QueueJob]:
        ...

    @abstractmethod
    def list_jobs(self, *, status: Optional[str] = None, limit: int = 50) -> List[QueueJob]:
        ...

    @abstractmethod
    def process_next(self, handlers: Dict[str, Callable[[QueueJob], Any]]) -> Optional[QueueJob]:
        ...


class InMemoryJobQueue(JobQueue):
    """Cola en memoria thread-safe para desarrollo local."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, QueueJob] = {}
        self._order: List[str] = []

    def enqueue(
        self,
        tipo: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        user_id: Optional[int] = None,
        max_attempts: int = 3,
    ) -> QueueJob:
        job = QueueJob(
            id=str(uuid.uuid4()),
            tipo=tipo,
            payload=payload or {},
            user_id=user_id,
            max_attempts=max_attempts,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
        return job

    def get(self, job_id: str) -> Optional[QueueJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, *, status: Optional[str] = None, limit: int = 50) -> List[QueueJob]:
        with self._lock:
            items = list(self._jobs.values())
        if status:
            items = [j for j in items if j.status == status]
        items.sort(key=lambda j: j.created_at, reverse=True)
        return items[:limit]

    def process_next(self, handlers: Dict[str, Callable[[QueueJob], Any]]) -> Optional[QueueJob]:
        with self._lock:
            candidate: Optional[QueueJob] = None
            for jid in self._order:
                job = self._jobs[jid]
                if job.status in ("queued", "retry"):
                    candidate = job
                    candidate.status = "processing"
                    candidate.attempts += 1
                    candidate.updated_at = datetime.now(timezone.utc)
                    break
        if not candidate:
            return None

        handler = handlers.get(candidate.tipo)
        try:
            if not handler:
                raise ValueError(f"Sin handler para tipo '{candidate.tipo}'")
            result = handler(candidate)
            with self._lock:
                candidate.status = "completed"
                candidate.result = result
                candidate.error = None
                candidate.updated_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                candidate.error = str(exc)
                candidate.updated_at = datetime.now(timezone.utc)
                if candidate.attempts < candidate.max_attempts:
                    candidate.status = "retry"
                else:
                    candidate.status = "failed"
        return candidate


_shared_queue: Optional[InMemoryJobQueue] = None
_shared_lock = threading.Lock()


def get_shared_queue() -> InMemoryJobQueue:
    global _shared_queue
    with _shared_lock:
        if _shared_queue is None:
            _shared_queue = InMemoryJobQueue()
        return _shared_queue
