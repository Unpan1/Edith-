"""Panel admin: usuarios, jobs y stats."""

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import Job, Plan, ScheduledPost
from app.models.user import User
from app.models.video import Video
from app.modules.admin.schemas import (
    AdminJobItem,
    AdminOverview,
    AdminUserItem,
    SystemStats,
)


class AdminService:
    """Stubs de administración del sistema."""

    def overview(self, db: Session) -> AdminOverview:
        stats = SystemStats(
            users=db.query(User).count(),
            videos=db.query(Video).count(),
            clips=db.query(Clip).count(),
            jobs=db.query(Job).count(),
            scheduled_posts=db.query(ScheduledPost).count(),
            plans=db.query(Plan).count(),
        )
        users = db.query(User).order_by(User.id.asc()).limit(50).all()
        jobs = db.query(Job).order_by(Job.created_at.desc()).limit(20).all()
        return AdminOverview(
            stats=stats,
            users=[AdminUserItem.model_validate(u) for u in users],
            recent_jobs=[
                AdminJobItem(
                    id=j.id,
                    tipo=j.tipo,
                    status=j.status.value if hasattr(j.status, "value") else str(j.status),
                    attempts=j.attempts,
                    error=j.error,
                )
                for j in jobs
            ],
        )
