"""Rutas del editor."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.editor.schemas import ClipEditorRead, ClipEditorUpdate
from app.modules.editor.service import EditorService

router = APIRouter(prefix="/api/editor", tags=["editor"])


@router.get("/clips/{clip_id}", response_model=ClipEditorRead)
def get_clip_editor(clip_id: int, db: Session = Depends(get_db)):
    return EditorService().get(db, clip_id)


@router.patch("/clips/{clip_id}", response_model=ClipEditorRead)
def update_clip_editor(
    clip_id: int,
    body: ClipEditorUpdate,
    db: Session = Depends(get_db),
):
    return EditorService().update(db, clip_id, body)
