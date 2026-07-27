"""Rutas de learning."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.deps import get_current_user_id
from app.modules.learning.schemas import LearningGenerateResponse, LearningInsightRead
from app.modules.learning.service import LearningService

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/insights", response_model=List[LearningInsightRead])
def list_insights(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return LearningService().list_insights(db, user_id)


@router.post("/generate", response_model=LearningGenerateResponse)
def generate_insights(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = LearningService().generate(db, user_id)
    return LearningGenerateResponse(
        insights=[LearningInsightRead.model_validate(r) for r in rows]
    )
