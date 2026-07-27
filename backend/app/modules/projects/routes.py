"""Rutas de proyectos."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.deps import get_current_user_id
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.projects.service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return ProjectService().list(db, user_id)


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return ProjectService().create(db, user_id, body)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return ProjectService().get(db, project_id, user_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return ProjectService().update(db, project_id, user_id, body)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    ProjectService().delete(db, project_id, user_id)
