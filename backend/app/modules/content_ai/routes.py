"""Rutas de contenido AI."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.content_ai.schemas import ClipContentRead, ContentGenerateRequest
from app.modules.content_ai.service import ContentAiService

router = APIRouter(prefix="/api/content", tags=["content"])


def get_content_ai_service() -> ContentAiService:
    return ContentAiService()


@router.post("/generate", response_model=ClipContentRead)
def generate_content(
    body: ContentGenerateRequest,
    db: Session = Depends(get_db),
    service: ContentAiService = Depends(get_content_ai_service),
):
    """Genera títulos, descripciones y hashtags para un clip."""
    return service.generate_for_clip(db, body.clip_id)


@router.get("/clips/{clip_id}", response_model=ClipContentRead)
def get_content(
    clip_id: int,
    db: Session = Depends(get_db),
    service: ContentAiService = Depends(get_content_ai_service),
):
    return service.get_for_clip(db, clip_id)
