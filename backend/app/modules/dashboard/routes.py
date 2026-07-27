"""Rutas del dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.dashboard.schemas import DashboardStats
from app.modules.dashboard.service import DashboardService
from app.modules.deps import get_current_user_id

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return DashboardService().stats(db, user_id)
