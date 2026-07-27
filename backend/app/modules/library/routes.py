"""Rutas de biblioteca."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.library.schemas import LibraryResponse
from app.modules.library.service import LibraryService

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=LibraryResponse)
def library(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    video_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return LibraryService().list_media(
        db, q=q, status=status, video_id=video_id, limit=limit
    )
