"""CRUD de publicaciones programadas y cuentas sociales (stub)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.saas import Platform, PostStatus, ScheduledPost, SocialAccount
from app.modules.deps import DEFAULT_USER_ID
from app.utils.exceptions import AppError


class PublishingService:
    """Gestión de posts y cuentas (sin OAuth real)."""

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        clip_id: Optional[int],
        platform: Platform,
        status: PostStatus = PostStatus.DRAFT,
        titulo: Optional[str] = None,
        descripcion: Optional[str] = None,
        hashtags: Optional[list] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> ScheduledPost:
        if status == PostStatus.SCHEDULED and not scheduled_at:
            raise AppError("scheduled_at requerido para estado scheduled")
        post = ScheduledPost(
            user_id=user_id,
            clip_id=clip_id,
            platform=platform,
            status=status,
            titulo=titulo,
            descripcion=descripcion,
            hashtags=hashtags,
            scheduled_at=scheduled_at,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    def list_posts(
        self,
        db: Session,
        user_id: int = DEFAULT_USER_ID,
        status: Optional[PostStatus] = None,
    ) -> List[ScheduledPost]:
        q = db.query(ScheduledPost).filter(ScheduledPost.user_id == user_id)
        if status:
            q = q.filter(ScheduledPost.status == status)
        return q.order_by(ScheduledPost.fecha.desc()).all()

    def get(self, db: Session, post_id: int, user_id: int = DEFAULT_USER_ID) -> ScheduledPost:
        post = (
            db.query(ScheduledPost)
            .filter(ScheduledPost.id == post_id, ScheduledPost.user_id == user_id)
            .first()
        )
        if not post:
            raise AppError(f"Post {post_id} no encontrado", status_code=404)
        return post

    def update(
        self,
        db: Session,
        post_id: int,
        *,
        user_id: int = DEFAULT_USER_ID,
        status: Optional[PostStatus] = None,
        titulo: Optional[str] = None,
        descripcion: Optional[str] = None,
        hashtags: Optional[list] = None,
        scheduled_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> ScheduledPost:
        post = self.get(db, post_id, user_id)
        if status is not None:
            post.status = status
            if status == PostStatus.PUBLISHED:
                post.published_at = datetime.now(timezone.utc)
        if titulo is not None:
            post.titulo = titulo
        if descripcion is not None:
            post.descripcion = descripcion
        if hashtags is not None:
            post.hashtags = hashtags
        if scheduled_at is not None:
            post.scheduled_at = scheduled_at
        if error_message is not None:
            post.error_message = error_message
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    def delete(self, db: Session, post_id: int, user_id: int = DEFAULT_USER_ID) -> None:
        post = self.get(db, post_id, user_id)
        db.delete(post)
        db.commit()

    def connect_account(
        self, db: Session, user_id: int, platform: Platform, handle: str
    ) -> SocialAccount:
        acc = (
            db.query(SocialAccount)
            .filter(SocialAccount.user_id == user_id, SocialAccount.platform == platform)
            .first()
        )
        if acc:
            acc.handle = handle
            acc.connected = True
        else:
            acc = SocialAccount(
                user_id=user_id, platform=platform, handle=handle, connected=True
            )
            db.add(acc)
        db.commit()
        db.refresh(acc)
        return acc

    def list_accounts(self, db: Session, user_id: int) -> List[SocialAccount]:
        return db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()
