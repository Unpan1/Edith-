"""Rutas de analytics."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.analytics.schemas import (
    AnalyticsSnapshotCreate,
    AnalyticsSnapshotRead,
    RankingResponse,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.deps import get_current_user_id

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/snapshots", response_model=List[AnalyticsSnapshotRead])
def list_snapshots(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return AnalyticsService().list_snapshots(db, user_id, limit)


@router.post("/snapshots", response_model=AnalyticsSnapshotRead, status_code=201)
def create_snapshot(
    body: AnalyticsSnapshotCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return AnalyticsService().create(db, user_id, body)


@router.get("/ranking", response_model=RankingResponse)
def ranking(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return AnalyticsService().ranking(db, user_id, limit)
