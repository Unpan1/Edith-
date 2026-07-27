"""Servicio de enriquecimiento post-generación de clips."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.saas import AutomationSettings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentEnrichmentService:
    """Orquesta AI de contenido + miniaturas + stubs de publicación."""

    def enrich_clip(self, db: Session, clip_id: int, user_id: int = 1) -> dict:
        """Enriquece un clip: contenido AI, thumbnail y opcional schedule stub."""
        from app.modules.content_ai.service import ContentAiService
        from app.modules.thumbnails.service import ThumbnailService
        from app.modules.publishing.service import PublishingService
        from app.models.saas import Platform, PostStatus
        from datetime import datetime, timedelta, timezone

        result: dict = {"clip_id": clip_id, "content": None, "thumbnail": None, "scheduled": None}

        settings = (
            db.query(AutomationSettings)
            .filter(AutomationSettings.user_id == user_id)
            .first()
        )
        do_enrich = True if settings is None else settings.enrich_after_process
        do_thumbs = True if settings is None else settings.auto_thumbnails
        do_schedule = False if settings is None else settings.auto_schedule_stubs
        platforms = (settings.default_platforms if settings and settings.default_platforms else ["tiktok"])

        if do_enrich:
            content = ContentAiService().generate_for_clip(db, clip_id)
            result["content"] = content.id if content else None

        if do_thumbs:
            thumb = ThumbnailService().ensure_thumbnail(db, clip_id)
            result["thumbnail"] = thumb.id if thumb else None

        if do_schedule and result.get("content"):
            pub = PublishingService()
            for p in platforms[:2]:
                try:
                    platform = Platform(p) if isinstance(p, str) else p
                except ValueError:
                    continue
                post = pub.create(
                    db,
                    user_id=user_id,
                    clip_id=clip_id,
                    platform=platform,
                    status=PostStatus.DRAFT,
                    scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
                )
                result["scheduled"] = post.id

        logger.info("Clip #%d enriquecido: %s", clip_id, result)
        return result

    def enrich_video_clips(self, db: Session, video_id: int, user_id: int = 1) -> list[dict]:
        """Descuenta créditos y enriquece todos los clips de un video."""
        from app.models.clip import Clip
        from app.modules.credits.service import CreditsService

        try:
            CreditsService().bootstrap(db, user_id)
            CreditsService().deduct_for_process(db, user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Deducción de créditos video #%d: %s", video_id, exc)

        clips = db.query(Clip).filter(Clip.video_id == video_id).all()
        results = []
        for clip in clips:
            try:
                results.append(self.enrich_clip(db, clip.id, user_id=user_id))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Enrich falló clip #%d: %s", clip.id, exc)
                results.append({"clip_id": clip.id, "error": str(exc)})
        return results
