"""Agente de growth: plan multi-plataforma a partir de instrucción + video."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.video import Video
from app.modules.deps import DEFAULT_USER_ID
from app.modules.growth_agent.schemas import GrowthPlanResult
from app.modules.jobs.service import JobsService
from app.modules.publishing.service import PublishingService
from app.models.saas import Platform, PostStatus
from app.utils.exceptions import VideoNotFoundError


class GrowthAgentService:
    """Sugiere plan multi-plataforma usando opciones de process existentes."""

    def enqueue_plan(
        self,
        db: Session,
        *,
        instruction: str,
        video_id: int,
        user_id: int = DEFAULT_USER_ID,
    ) -> int:
        video = db.get(Video, video_id)
        if not video:
            raise VideoNotFoundError(video_id)
        job = JobsService().enqueue(
            db,
            tipo="growth_plan",
            payload={"instruction": instruction, "video_id": video_id},
            user_id=user_id,
        )
        return job.id

    def run_plan(
        self,
        db: Session,
        *,
        instruction: str,
        video_id: int,
        user_id: int = DEFAULT_USER_ID,
    ) -> Dict[str, Any]:
        video = db.get(Video, video_id)
        if not video:
            raise VideoNotFoundError(video_id)

        text = instruction.lower()
        platforms: List[str] = []
        if "tiktok" in text or "todo" in text or "todas" in text:
            platforms.append("tiktok")
        if "instagram" in text or "reels" in text or "todas" in text:
            platforms.append("instagram")
        if "youtube" in text or "shorts" in text or "todas" in text:
            platforms.append("shorts")
        if "linkedin" in text:
            platforms.append("linkedin")
        if not platforms:
            platforms = ["tiktok", "shorts", "instagram"]

        max_clips = 8 if "más clips" in text or "more" in text else 5
        if "corto" in text or "short" in text:
            min_d, max_d = 15.0, 35.0
        else:
            min_d, max_d = 20.0, 60.0

        suggested_options: Dict[str, Any] = {
            "max_clips": max_clips,
            "min_clip_duration": min_d,
            "max_clip_duration": max_d,
            "formats": ["vertical_9_16"] if "vertical" in text or True else ["landscape_16_9"],
            "burn_subtitles": "subtit" in text or True,
            "language": "es" if "español" in text or "spanish" in text else None,
        }

        notes = [
            f"Video '{video.nombre_original}' listo para plan de growth.",
            f"Plataformas objetivo: {', '.join(platforms)}.",
            "Usa POST /videos/{id}/process con suggested_options.",
        ]

        pub = PublishingService()
        stubs: List[Dict[str, Any]] = []
        for i, p in enumerate(platforms):
            try:
                platform = Platform(p)
            except ValueError:
                continue
            post = pub.create(
                db,
                user_id=user_id,
                clip_id=None,
                platform=platform,
                status=PostStatus.DRAFT,
                titulo=f"Growth: {instruction[:80]}",
                descripcion=f"Auto-plan para video #{video_id}",
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=i + 1),
            )
            stubs.append({"post_id": post.id, "platform": p})

        result = GrowthPlanResult(
            video_id=video_id,
            instruction=instruction,
            platforms=platforms,
            suggested_options=suggested_options,
            schedule_stubs=stubs,
            notes=notes,
        )
        return result.model_dump()
