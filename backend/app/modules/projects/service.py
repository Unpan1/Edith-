"""CRUD de proyectos."""

from typing import List

from sqlalchemy.orm import Session

from app.models.saas import Project
from app.modules.deps import DEFAULT_USER_ID
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.utils.exceptions import AppError


class ProjectService:
    """Proyectos del usuario."""

    def create(self, db: Session, user_id: int, body: ProjectCreate) -> Project:
        row = Project(user_id=user_id, nombre=body.nombre, descripcion=body.descripcion)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def list(self, db: Session, user_id: int = DEFAULT_USER_ID) -> List[Project]:
        return (
            db.query(Project)
            .filter(Project.user_id == user_id)
            .order_by(Project.fecha_creacion.desc())
            .all()
        )

    def get(self, db: Session, project_id: int, user_id: int = DEFAULT_USER_ID) -> Project:
        row = (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )
        if not row:
            raise AppError(f"Proyecto {project_id} no encontrado", status_code=404)
        return row

    def update(
        self, db: Session, project_id: int, user_id: int, body: ProjectUpdate
    ) -> Project:
        row = self.get(db, project_id, user_id)
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def delete(self, db: Session, project_id: int, user_id: int) -> None:
        row = self.get(db, project_id, user_id)
        db.delete(row)
        db.commit()
