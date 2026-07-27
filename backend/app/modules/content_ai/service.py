"""Generación local heurística de títulos, descripciones y hashtags."""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.saas import ClipContent
from app.models.transcription import Transcription
from app.utils.exceptions import AppError, ClipNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)

STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "a", "en", "que", "por", "con", "para", "se", "es", "son", "como",
    "más", "mas", "pero", "si", "no", "ya", "lo", "su", "sus", "me", "te", "le",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "this", "that", "it", "with", "as", "be", "was", "were", "from", "at",
    "you", "we", "they", "i", "he", "she", "my", "your", "our",
}

HOOKS = [
    "Esto cambiará cómo ves",
    "Nadie te cuenta esto sobre",
    "La verdad detrás de",
    "En 60 segundos: todo sobre",
    "Si ignoras esto sobre",
]

CTAS = [
    "Sígueme para más tips diarios",
    "Guarda este video y compártelo",
    "Comenta tu experiencia abajo",
    "Dale like si te sirvió",
    "Activa la campanita para no perdértelo",
]


class ContentAiService:
    """Heurísticas locales — sin OpenAI externo."""

    def generate_for_clip(self, db: Session, clip_id: int) -> ClipContent:
        clip = db.get(Clip, clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        text = self._clip_transcript(db, clip)
        titles = self._viral_titles(text, clip)
        descriptions = self._descriptions(text, titles)
        hashtags = self._hashtags(text)
        keywords = self._seo_keywords(text)
        cta = self._cta(text)

        existing = db.query(ClipContent).filter(ClipContent.clip_id == clip_id).first()
        if existing:
            existing.titles = titles
            existing.descriptions = descriptions
            existing.hashtags = hashtags
            existing.cta = cta
            existing.seo_keywords = keywords
            row = existing
        else:
            row = ClipContent(
                clip_id=clip_id,
                titles=titles,
                descriptions=descriptions,
                hashtags=hashtags,
                cta=cta,
                seo_keywords=keywords,
            )
            db.add(row)

        if not clip.titulo_generado and titles:
            clip.titulo_generado = titles[0]
            db.add(clip)

        db.commit()
        db.refresh(row)
        logger.info("Contenido AI generado para clip #%d", clip_id)
        return row

    def get_for_clip(self, db: Session, clip_id: int) -> ClipContent:
        row = db.query(ClipContent).filter(ClipContent.clip_id == clip_id).first()
        if not row:
            raise AppError(f"Sin contenido AI para clip {clip_id}", status_code=404)
        return row

    def _clip_transcript(self, db: Session, clip: Clip) -> str:
        tr = (
            db.query(Transcription)
            .filter(Transcription.video_id == clip.video_id)
            .order_by(Transcription.fecha.desc())
            .first()
        )
        if not tr or not tr.texto:
            return clip.titulo_generado or f"Clip {clip.id}"

        if tr.segmentos:
            parts: List[str] = []
            for seg in tr.segmentos:
                start = float(seg.get("start", 0))
                end = float(seg.get("end", start))
                if end >= clip.inicio and start <= clip.fin:
                    parts.append(str(seg.get("text", "")).strip())
            if parts:
                return " ".join(parts)

        return tr.texto[:2000]

    def _tokens(self, text: str) -> List[str]:
        words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]{3,}", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def _top_phrases(self, text: str, n: int = 5) -> List[str]:
        tokens = self._tokens(text)
        if not tokens:
            return ["contenido viral"]
        counts = Counter(tokens)
        return [w for w, _ in counts.most_common(n)]

    def _viral_titles(self, text: str, clip: Clip) -> List[str]:
        phrases = self._top_phrases(text, 4)
        topic = " ".join(phrases[:2]).title() if phrases else "Este Momento"
        dur = int(clip.duracion or 30)
        titles = [
            f"{HOOKS[0]} {topic}",
            f"{HOOKS[1]} {phrases[0].title() if phrases else 'esto'} ({dur}s)",
            f"{HOOKS[2]} {topic}",
        ]
        return [t[:120] for t in titles]

    def _descriptions(self, text: str, titles: List[str]) -> List[str]:
        snippet = re.sub(r"\s+", " ", text).strip()[:220]
        phrases = self._top_phrases(text, 3)
        topic = ", ".join(phrases) if phrases else "contenido"
        return [
            f"{titles[0]}. {snippet}…",
            f"Descubre por qué {topic} está en tendencia. {snippet[:140]}…",
            f"Resumen rápido: {snippet[:180]}… ¿Qué opinas?",
        ]

    def _hashtags(self, text: str) -> List[str]:
        phrases = self._top_phrases(text, 10)
        base = ["#viral", "#fyp", "#shorts", "#reels", "#clipai"]
        dynamic = [f"#{p}" for p in phrases if p.isalpha()]
        seen = set()
        out: List[str] = []
        for h in base + dynamic:
            key = h.lower()
            if key not in seen:
                seen.add(key)
                out.append(h)
            if len(out) >= 15:
                break
        while len(out) < 15:
            out.append(f"#trend{len(out)}")
        return out[:15]

    def _seo_keywords(self, text: str) -> List[str]:
        return self._top_phrases(text, 8)

    def _cta(self, text: str) -> str:
        tokens = self._tokens(text)
        idx = (len(tokens) or 1) % len(CTAS)
        return CTAS[idx]
