"""Rutas de admin."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.admin.schemas import AdminOverview
from app.modules.admin.service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverview)
def admin_overview(db: Session = Depends(get_db)):
    return AdminService().overview(db)
