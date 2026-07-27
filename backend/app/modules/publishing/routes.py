"""Rutas de publicación."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.saas import PostStatus
from app.modules.deps import get_current_user_id
from app.modules.publishing.schemas import (
    ScheduledPostCreate,
    ScheduledPostRead,
    ScheduledPostUpdate,
    SocialAccountConnect,
    SocialAccountRead,
)
from app.modules.publishing.service import PublishingService

router = APIRouter(prefix="/api/publishing", tags=["publishing"])


@router.get("/posts", response_model=List[ScheduledPostRead])
def list_posts(
    status: Optional[PostStatus] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return PublishingService().list_posts(db, user_id, status)


@router.post("/posts", response_model=ScheduledPostRead, status_code=201)
def create_post(
    body: ScheduledPostCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return PublishingService().create(
        db,
        user_id=user_id,
        clip_id=body.clip_id,
        platform=body.platform,
        status=body.status,
        titulo=body.titulo,
        descripcion=body.descripcion,
        hashtags=body.hashtags,
        scheduled_at=body.scheduled_at,
    )


@router.get("/posts/{post_id}", response_model=ScheduledPostRead)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return PublishingService().get(db, post_id, user_id)


@router.patch("/posts/{post_id}", response_model=ScheduledPostRead)
def update_post(
    post_id: int,
    body: ScheduledPostUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return PublishingService().update(
        db, post_id, user_id=user_id, **body.model_dump(exclude_unset=True)
    )


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    PublishingService().delete(db, post_id, user_id)


@router.post("/accounts/connect", response_model=SocialAccountRead)
def connect_account(
    body: SocialAccountConnect,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Stub de conexión OAuth — marca cuenta como connected."""
    return PublishingService().connect_account(db, user_id, body.platform, body.handle)


@router.get("/accounts", response_model=List[SocialAccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return PublishingService().list_accounts(db, user_id)
