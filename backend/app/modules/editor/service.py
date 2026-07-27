"""Editor ligero de metadatos de clip (no altera el pipeline de corte)."""

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import Caption
from app.modules.editor.schemas import ClipEditorRead, ClipEditorUpdate
from app.utils.exceptions import ClipNotFoundError


class EditorService:
    """Lee/actualiza título y captions asociados."""

    def get(self, db: Session, clip_id: int) -> ClipEditorRead:
        clip = db.get(Clip, clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)
        cap = db.query(Caption).filter(Caption.clip_id == clip_id).first()
        return ClipEditorRead(
            clip_id=clip.id,
            titulo_generado=clip.titulo_generado,
            inicio=clip.inicio,
            fin=clip.fin,
            duracion=clip.duracion,
            formato=clip.formato,
            ruta_clip=clip.ruta_clip,
            ruta_miniatura=clip.ruta_miniatura,
            caption_texto=cap.texto if cap else None,
            caption_estilo=cap.estilo if cap else None,
            caption_idioma=cap.idioma if cap else None,
        )

    def update(self, db: Session, clip_id: int, body: ClipEditorUpdate) -> ClipEditorRead:
        clip = db.get(Clip, clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)
        if body.titulo_generado is not None:
            clip.titulo_generado = body.titulo_generado
            db.add(clip)

        if any(
            v is not None
            for v in (body.caption_texto, body.caption_estilo, body.caption_idioma)
        ):
            cap = db.query(Caption).filter(Caption.clip_id == clip_id).first()
            if not cap:
                cap = Caption(clip_id=clip_id)
            if body.caption_texto is not None:
                cap.texto = body.caption_texto
            if body.caption_estilo is not None:
                cap.estilo = body.caption_estilo
            if body.caption_idioma is not None:
                cap.idioma = body.caption_idioma
            db.add(cap)

        db.commit()
        return self.get(db, clip_id)
