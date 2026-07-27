"""Insights heurísticos desde analytics y clips."""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import AnalyticsSnapshot, LearningInsight
from app.modules.deps import DEFAULT_USER_ID
from app.modules.learning.schemas import LearningInsightRead


class LearningService:
    """Genera recomendaciones de mejora de contenido."""

    def list_insights(self, db: Session, user_id: int = DEFAULT_USER_ID) -> List[LearningInsight]:
        return (
            db.query(LearningInsight)
            .filter(LearningInsight.user_id == user_id)
            .order_by(LearningInsight.fecha.desc())
            .all()
        )

    def generate(self, db: Session, user_id: int = DEFAULT_USER_ID) -> List[LearningInsight]:
        snaps = (
            db.query(AnalyticsSnapshot)
            .filter(AnalyticsSnapshot.user_id == user_id)
            .order_by(AnalyticsSnapshot.fecha.desc())
            .limit(20)
            .all()
        )
        clips = db.query(Clip).order_by(Clip.score.desc()).limit(10).all()
        insights: List[LearningInsight] = []

        if snaps:
            top = max(snaps, key=lambda s: s.views + s.likes * 2)
            insights.append(
                LearningInsight(
                    user_id=user_id,
                    clip_id=top.clip_id,
                    insight_type="top_performer",
                    titulo="Tu clip con mejor engagement",
                    detalle=(
                        f"Prioriza formatos similares: {top.views} views y {top.likes} likes. "
                        "Publica en horarios similares y refuerza el gancho inicial."
                    ),
                    score=float(top.views + top.likes * 2),
                )
            )
            avg_watch = sum(s.watch_time_sec for s in snaps) / max(len(snaps), 1)
            insights.append(
                LearningInsight(
                    user_id=user_id,
                    insight_type="retention",
                    titulo="Retención media de audiencia",
                    detalle=(
                        f"Watch time medio ~{avg_watch:.0f}s. Acorta intros y coloca CTA a los 8–12s."
                    ),
                    score=avg_watch,
                )
            )

        if clips:
            best = clips[0]
            insights.append(
                LearningInsight(
                    user_id=user_id,
                    clip_id=best.id,
                    insight_type="score",
                    titulo="Clip con mayor score interno",
                    detalle=(
                        f"Duración {best.duracion:.0f}s y score {best.score:.2f}. "
                        "Replica estructura: gancho → valor → CTA."
                    ),
                    score=best.score,
                )
            )
            short = [c for c in clips if c.duracion and c.duracion < 35]
            if short:
                insights.append(
                    LearningInsight(
                        user_id=user_id,
                        insight_type="duration",
                        titulo="Clips cortos rinden bien",
                        detalle=(
                            f"{len(short)} clips <35s detectados. Ideal para TikTok/Reels/Shorts."
                        ),
                        score=float(len(short)),
                    )
                )

        if not insights:
            insights.append(
                LearningInsight(
                    user_id=user_id,
                    insight_type="bootstrap",
                    titulo="Empieza a generar clips",
                    detalle="Procesa un video para obtener insights personalizados.",
                    score=0.0,
                )
            )

        for row in insights:
            db.add(row)
        db.commit()
        for row in insights:
            db.refresh(row)
        return insights
