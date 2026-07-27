"""Rutas del growth agent."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.deps import get_current_user_id
from app.modules.growth_agent.schemas import GrowthEnqueueResponse, GrowthPlanRequest
from app.modules.growth_agent.service import GrowthAgentService

router = APIRouter(prefix="/api/growth", tags=["growth"])


@router.post("/plan", response_model=GrowthEnqueueResponse)
def enqueue_growth_plan(
    body: GrowthPlanRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Encola un job que genera plan multi-plataforma."""
    job_id = GrowthAgentService().enqueue_plan(
        db,
        instruction=body.instruction,
        video_id=body.video_id,
        user_id=user_id,
    )
    return GrowthEnqueueResponse(job_id=job_id)


@router.post("/plan/sync")
def run_growth_plan_sync(
    body: GrowthPlanRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Ejecuta el plan de forma síncrona (debug)."""
    return GrowthAgentService().run_plan(
        db,
        instruction=body.instruction,
        video_id=body.video_id,
        user_id=user_id,
    )
