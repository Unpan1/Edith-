"""Rutas de créditos."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.credits.schemas import CreditsBalance, PlanRead
from app.modules.credits.service import CreditsService
from app.modules.deps import get_current_user_id

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/balance", response_model=CreditsBalance)
def balance(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return CreditsService().get_balance_view(db, user_id)


@router.get("/plans", response_model=List[PlanRead])
def plans(db: Session = Depends(get_db)):
    CreditsService().bootstrap(db)
    return CreditsService().list_plans(db)
