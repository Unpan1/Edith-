"""Rutas de miniaturas."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.thumbnails.schemas import ThumbnailCreate, ThumbnailRead
from app.modules.thumbnails.service import ThumbnailService

router = APIRouter(prefix="/api/thumbnails", tags=["thumbnails"])


def get_thumbnail_service() -> ThumbnailService:
    return ThumbnailService()


@router.post("", response_model=ThumbnailRead, status_code=201)
def create_thumbnail(
    body: ThumbnailCreate,
    db: Session = Depends(get_db),
    service: ThumbnailService = Depends(get_thumbnail_service),
):
    return service.ensure_thumbnail(
        db, body.clip_id, texto_overlay=body.texto_overlay, at_seconds=body.at_seconds
    )


@router.get("/clips/{clip_id}", response_model=List[ThumbnailRead])
def list_thumbnails(
    clip_id: int,
    db: Session = Depends(get_db),
    service: ThumbnailService = Depends(get_thumbnail_service),
):
    return service.list_for_clip(db, clip_id)
