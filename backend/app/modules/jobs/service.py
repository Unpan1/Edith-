"""Servicio de jobs en DB + cola in-memory."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.saas import Job, JobStatus
from app.modules.deps import DEFAULT_USER_ID
from app.modules.jobs.queue import InMemoryJobQueue, QueueJob, get_shared_queue
from app.utils.exceptions import AppError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobsService:
    """Encola y procesa trabajos con estados ORM."""

    def __init__(self, queue: Optional[InMemoryJobQueue] = None):
        self.queue = queue or get_shared_queue()

    def enqueue(
        self,
        db: Session,
        *,
        tipo: str,
        payload: Optional[Dict[str, Any]] = None,
        user_id: int = DEFAULT_USER_ID,
        max_attempts: int = 3,
    ) -> Job:
        qjob = self.queue.enqueue(
            tipo, payload or {}, user_id=user_id, max_attempts=max_attempts
        )
        row = Job(
            user_id=user_id,
            tipo=tipo,
            payload={**(payload or {}), "_queue_id": qjob.id},
            status=JobStatus.QUEUED,
            attempts=0,
            max_attempts=max_attempts,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("Job #%d encolado tipo=%s queue=%s", row.id, tipo, qjob.id)
        return row

    def get(self, db: Session, job_id: int) -> Job:
        row = db.get(Job, job_id)
        if not row:
            raise AppError(f"Job {job_id} no encontrado", status_code=404)
        return row

    def list_jobs(
        self,
        db: Session,
        *,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[Job]:
        q = db.query(Job).order_by(Job.created_at.desc())
        if status:
            q = q.filter(Job.status == status)
        return q.limit(limit).all()

    def _default_handlers(self, db: Session) -> Dict[str, Callable[[QueueJob], Any]]:
        def enrich_handler(qjob: QueueJob) -> Any:
            from app.modules.content_ai.enrichment import ContentEnrichmentService

            clip_id = int(qjob.payload.get("clip_id", 0))
            video_id = qjob.payload.get("video_id")
            svc = ContentEnrichmentService()
            if clip_id:
                return svc.enrich_clip(db, clip_id, user_id=qjob.user_id or 1)
            if video_id:
                return svc.enrich_video_clips(db, int(video_id), user_id=qjob.user_id or 1)
            raise ValueError("clip_id o video_id requerido")

        def growth_handler(qjob: QueueJob) -> Any:
            from app.modules.growth_agent.service import GrowthAgentService

            return GrowthAgentService().run_plan(
                db,
                instruction=str(qjob.payload.get("instruction", "")),
                video_id=int(qjob.payload.get("video_id", 0)),
                user_id=qjob.user_id or 1,
            )

        def noop_handler(qjob: QueueJob) -> Any:
            return {"ok": True, "payload": qjob.payload}

        return {
            "enrich_clip": enrich_handler,
            "enrich_video": enrich_handler,
            "growth_plan": growth_handler,
            "noop": noop_handler,
        }

    def process_next(self, db: Session) -> Optional[Job]:
        handlers = self._default_handlers(db)
        qjob = self.queue.process_next(handlers)
        if not qjob:
            return None

        row = None
        for candidate in (
            db.query(Job).order_by(Job.created_at.desc()).limit(100).all()
        ):
            payload = candidate.payload or {}
            if payload.get("_queue_id") == qjob.id:
                row = candidate
                break

        if not row:
            # create orphan sync row
            row = Job(
                user_id=qjob.user_id,
                tipo=qjob.tipo,
                payload={**qjob.payload, "_queue_id": qjob.id},
                status=JobStatus.QUEUED,
            )
            db.add(row)
            db.flush()

        status_map = {
            "processing": JobStatus.PROCESSING,
            "completed": JobStatus.COMPLETED,
            "failed": JobStatus.FAILED,
            "retry": JobStatus.RETRY,
            "queued": JobStatus.QUEUED,
        }
        row.status = status_map.get(qjob.status, JobStatus.FAILED)
        row.attempts = qjob.attempts
        row.result = qjob.result if isinstance(qjob.result, (dict, list)) else {"value": qjob.result}
        row.error = qjob.error
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
