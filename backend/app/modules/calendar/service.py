"""Listado de posts por mes."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.saas import ScheduledPost
from app.modules.calendar.schemas import CalendarMonthResponse
from app.modules.deps import DEFAULT_USER_ID
from app.modules.publishing.schemas import ScheduledPostRead


class CalendarService:
    """Calendario editorial."""

    def posts_by_month(
        self, db: Session, year: int, month: int, user_id: int = DEFAULT_USER_ID
    ) -> CalendarMonthResponse:
        posts = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.user_id == user_id,
                ScheduledPost.scheduled_at.isnot(None),
            )
            .all()
        )
        filtered = []
        for p in posts:
            sa: datetime = p.scheduled_at
            if sa and sa.year == year and sa.month == month:
                filtered.append(ScheduledPostRead.model_validate(p))
        filtered.sort(key=lambda x: x.scheduled_at or datetime.min)
        return CalendarMonthResponse(year=year, month=month, posts=filtered)
