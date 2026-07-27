"""Agregados del panel principal."""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import (
    CreditLedger,
    Job,
    JobStatus,
    Notification,
    PostStatus,
    ScheduledPost,
)
from app.models.video import Video, VideoStatus
from app.modules.dashboard.schemas import DashboardStats, RecentClipItem
from app.modules.deps import DEFAULT_USER_ID


class DashboardService:
    """Cuenta videos, clips, jobs, posts, créditos y actividad reciente."""

    def stats(self, db: Session, user_id: int = DEFAULT_USER_ID) -> DashboardStats:
        videos = db.query(Video).count()
        videos_completed = (
            db.query(Video).filter(Video.estado == VideoStatus.COMPLETED).count()
        )
        clips = db.query(Clip).count()
        minutes = float(db.query(func.coalesce(func.sum(Clip.duracion), 0)).scalar() or 0) / 60.0
        # Heurística: edición manual ~8× la duración del clip
        time_saved_hours = round((minutes * 8) / 60.0, 1)

        jobs_queued = (
            db.query(Job)
            .filter(Job.status.in_([JobStatus.QUEUED, JobStatus.RETRY]))
            .count()
        )
        jobs_processing = (
            db.query(Job).filter(Job.status == JobStatus.PROCESSING).count()
        )
        scheduled = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.user_id == user_id,
                ScheduledPost.status == PostStatus.SCHEDULED,
            )
            .count()
        )
        published = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.user_id == user_id,
                ScheduledPost.status == PostStatus.PUBLISHED,
            )
            .count()
        )
        last = (
            db.query(CreditLedger)
            .filter(CreditLedger.user_id == user_id)
            .order_by(CreditLedger.fecha.desc())
            .first()
        )
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        used_month = (
            db.query(func.coalesce(func.sum(CreditLedger.delta), 0))
            .filter(
                CreditLedger.user_id == user_id,
                CreditLedger.delta < 0,
                CreditLedger.fecha >= month_start,
            )
            .scalar()
        )
        unread = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.leida.is_(False))
            .count()
        )
        recent = (
            db.query(Clip).order_by(Clip.fecha.desc()).limit(8).all()
        )
        recent_clips = [
            RecentClipItem(
                id=c.id,
                titulo=c.titulo_generado,
                duracion=c.duracion,
                score=c.score,
                formato=c.formato,
                fecha=c.fecha,
            )
            for c in recent
        ]
        return DashboardStats(
            videos=videos,
            videos_completed=videos_completed,
            clips=clips,
            minutes_processed=round(minutes, 1),
            time_saved_hours=time_saved_hours,
            jobs_queued=jobs_queued,
            jobs_processing=jobs_processing,
            scheduled_posts=scheduled,
            published_posts=published,
            credits_balance=last.balance_after if last else 0,
            credits_used_month=abs(int(used_month or 0)),
            notifications_unread=unread,
            recent_clips=recent_clips,
        )
