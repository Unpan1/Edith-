"""Tendencias seed/mock con opportunity score."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.saas import TrendReport

SEED_TRENDS = [
    {
        "category": "tech",
        "country": "ES",
        "title": "IA generativa para creadores",
        "score": 92.5,
        "opportunity_score": 88.0,
        "data": {"keywords": ["ia", "clips", "automatización"], "growth": "+34%"},
    },
    {
        "category": "tech",
        "country": "MX",
        "title": "Shorts de productividad",
        "score": 84.0,
        "opportunity_score": 79.5,
        "data": {"keywords": ["productividad", "tips"], "growth": "+21%"},
    },
    {
        "category": "entertainment",
        "country": "GLOBAL",
        "title": "Reacciones en vertical",
        "score": 95.0,
        "opportunity_score": 71.0,
        "data": {"keywords": ["reaction", "viral"], "growth": "+12%"},
    },
    {
        "category": "education",
        "country": "ES",
        "title": "Micro-lecciones de 45s",
        "score": 78.2,
        "opportunity_score": 90.0,
        "data": {"keywords": ["educación", "microlearning"], "growth": "+41%"},
    },
    {
        "category": "fitness",
        "country": "MX",
        "title": "Rutinas en casa 30s",
        "score": 81.0,
        "opportunity_score": 85.5,
        "data": {"keywords": ["fitness", "casa"], "growth": "+18%"},
    },
    {
        "category": "finance",
        "country": "GLOBAL",
        "title": "Finanzas personales en clips",
        "score": 76.5,
        "opportunity_score": 82.0,
        "data": {"keywords": ["finanzas", "ahorro"], "growth": "+27%"},
    },
    {
        "category": "food",
        "country": "ES",
        "title": "Recetas express verticales",
        "score": 88.0,
        "opportunity_score": 74.0,
        "data": {"keywords": ["recetas", "cocina"], "growth": "+15%"},
    },
    {
        "category": "gaming",
        "country": "GLOBAL",
        "title": "Highlights competitivos",
        "score": 90.0,
        "opportunity_score": 68.0,
        "data": {"keywords": ["gaming", "highlights"], "growth": "+9%"},
    },
]


class TrendsService:
    """Devuelve tendencias filtrables; siembra si la tabla está vacía."""

    def ensure_seed(self, db: Session) -> None:
        if db.query(TrendReport).count() == 0:
            for t in SEED_TRENDS:
                db.add(TrendReport(**t))
            db.commit()

    def list_trends(
        self,
        db: Session,
        *,
        category: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> List[TrendReport]:
        self.ensure_seed(db)
        q = db.query(TrendReport)
        if category:
            q = q.filter(TrendReport.category == category.lower())
        if country:
            q = q.filter(TrendReport.country == country.upper())
        return (
            q.order_by(TrendReport.opportunity_score.desc())
            .limit(limit)
            .all()
        )
