"""Listado y filtros de videos/clips."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.video import Video, VideoStatus
from app.modules.library.schemas import LibraryClipItem, LibraryResponse, LibraryVideoItem


class LibraryService:
    """Biblioteca de medios."""

    def list_media(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        status: Optional[str] = None,
        video_id: Optional[int] = None,
        limit: int = 50,
    ) -> LibraryResponse:
        vq = db.query(Video).order_by(Video.fecha_subida.desc())
        if status:
            try:
                vq = vq.filter(Video.estado == VideoStatus(status))
            except ValueError:
                pass
        if q:
            vq = vq.filter(Video.nombre_original.ilike(f"%{q}%"))
        videos = vq.limit(limit).all()

        cq = db.query(Clip).order_by(Clip.fecha.desc())
        if video_id:
            cq = cq.filter(Clip.video_id == video_id)
        if q:
            cq = cq.filter(Clip.titulo_generado.ilike(f"%{q}%"))
        clips = cq.limit(limit).all()

        video_items: List[LibraryVideoItem] = []
        for v in videos:
            video_items.append(
                LibraryVideoItem(
                    id=v.id,
                    nombre_original=v.nombre_original,
                    duracion=v.duracion,
                    estado=v.estado.value if hasattr(v.estado, "value") else str(v.estado),
                    progreso=v.progreso,
                    fecha_subida=v.fecha_subida,
                    clips_count=len(v.clips) if v.clips is not None else 0,
                )
            )

        clip_items = [LibraryClipItem.model_validate(c) for c in clips]
        return LibraryResponse(videos=video_items, clips=clip_items)
