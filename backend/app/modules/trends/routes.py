"""Rutas de tendencias."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.trends.schemas import TrendReportRead, TrendsResponse
from app.modules.trends.service import TrendsService

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("", response_model=TrendsResponse)
def list_trends(
    category: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = TrendsService().list_trends(
        db, category=category, country=country, limit=limit
    )
    return TrendsResponse(items=[TrendReportRead.model_validate(i) for i in items])
