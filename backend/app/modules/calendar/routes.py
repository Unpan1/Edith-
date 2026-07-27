"""Rutas de calendario."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.calendar.schemas import CalendarMonthResponse
from app.modules.calendar.service import CalendarService
from app.modules.deps import get_current_user_id

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/month", response_model=CalendarMonthResponse)
def calendar_month(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return CalendarService().posts_by_month(db, year, month, user_id)
