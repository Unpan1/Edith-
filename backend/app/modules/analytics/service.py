"""Snapshots y ranking de métricas."""

from __future__ import annotations

import random
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import AnalyticsSnapshot, Platform
from app.modules.analytics.schemas import (
    AnalyticsSnapshotCreate,
    RankingItem,
    RankingResponse,
)
from app.modules.deps import DEFAULT_USER_ID


class AnalyticsService:
    """Almacena y lee snapshots; genera mock si vacío."""

    def create(
        self, db: Session, user_id: int, body: AnalyticsSnapshotCreate
    ) -> AnalyticsSnapshot:
        row = AnalyticsSnapshot(user_id=user_id, **body.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def list_snapshots(
        self, db: Session, user_id: int = DEFAULT_USER_ID, limit: int = 50
    ) -> List[AnalyticsSnapshot]:
        rows = (
            db.query(AnalyticsSnapshot)
            .filter(AnalyticsSnapshot.user_id == user_id)
            .order_by(AnalyticsSnapshot.fecha.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            rows = self.seed_mock(db, user_id)
        return rows

    def seed_mock(self, db: Session, user_id: int = DEFAULT_USER_ID) -> List[AnalyticsSnapshot]:
        clips = db.query(Clip).limit(5).all()
        created: List[AnalyticsSnapshot] = []
        platforms = list(Platform)
        targets = clips or [None]
        for i, clip in enumerate(targets):
            row = AnalyticsSnapshot(
                user_id=user_id,
                clip_id=clip.id if clip else None,
                video_id=clip.video_id if clip else None,
                platform=platforms[i % len(platforms)],
                views=random.randint(500, 50000),
                likes=random.randint(20, 4000),
                comments=random.randint(5, 400),
                shares=random.randint(1, 200),
                watch_time_sec=float(random.randint(1000, 80000)),
            )
            db.add(row)
            created.append(row)
        db.commit()
        for r in created:
            db.refresh(r)
        return created

    def ranking(self, db: Session, user_id: int = DEFAULT_USER_ID, limit: int = 10) -> RankingResponse:
        rows = self.list_snapshots(db, user_id, limit=100)
        items = []
        for r in rows:
            score = r.views * 1.0 + r.likes * 3.0 + r.comments * 5.0 + r.shares * 4.0
            items.append(
                RankingItem(
                    clip_id=r.clip_id,
                    video_id=r.video_id,
                    score=score,
                    views=r.views,
                    likes=r.likes,
                )
            )
        items.sort(key=lambda x: x.score, reverse=True)
        return RankingResponse(items=items[:limit])
