"""Rutas de automatización."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.automation.schemas import AutomationSettingsRead, AutomationSettingsUpdate
from app.modules.automation.service import AutomationService
from app.modules.deps import get_current_user_id

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.get("/settings", response_model=AutomationSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return AutomationService().get_or_create(db, user_id)


@router.patch("/settings", response_model=AutomationSettingsRead)
def update_settings(
    body: AutomationSettingsUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return AutomationService().update(db, user_id, body)
