"""Detector de highlights: identifica los mejores momentos de una transcripción."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from app.ai.whisper_service import WhisperSegment
from app.config.settings import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Palabras clave que suelen indicar momentos virales / interesantes
KEYWORD_WEIGHTS: Dict[str, float] = {
    # ES
    "increíble": 1.5, "impresionante": 1.5, "importante": 1.2, "secreto": 1.4,
    "nunca": 1.1, "siempre": 0.8, "mejor": 1.0, "peor": 1.0, "error": 1.1,
    "clave": 1.2, "truco": 1.4, "consejo": 1.2, "resultado": 1.0, "sorpresa": 1.5,
    "cuidado": 1.2, "atención": 1.3, "mira": 1.0, "escucha": 1.1, "verdad": 1.2,
    "mentira": 1.3, "historia": 1.0, "ejemplo": 0.9, "dinero": 1.2, "éxito": 1.2,
    "fracaso": 1.2, "amor": 1.0, "miedo": 1.1, "odio": 1.0, "feliz": 1.0,
    "triste": 1.0, "enojado": 1.1, "loco": 1.1, "genial": 1.3, "brutal": 1.4,
    "wtf": 1.5, "omg": 1.4, "wow": 1.3,
    # EN
    "amazing": 1.5, "incredible": 1.5, "important": 1.2, "secret": 1.4,
    "never": 1.1, "always": 0.8, "best": 1.0, "worst": 1.0, "mistake": 1.1,
    "tip": 1.3, "hack": 1.4, "result": 1.0, "surprise": 1.5, "careful": 1.2,
    "listen": 1.1, "truth": 1.2, "story": 1.0, "money": 1.2, "success": 1.2,
    "failure": 1.2, "crazy": 1.2, "insane": 1.4, "unbelievable": 1.5,
}

EMOTION_PATTERNS = [
    (re.compile(r"[!]{2,}"), 1.2),
    (re.compile(r"[?]{2,}"), 1.0),
    (re.compile(r"\b(jaj+|lol+|haha+|xd+)\b", re.I), 1.3),
    (re.compile(r"\b(omg|wtf|dios mío|no puede ser)\b", re.I), 1.5),
]


@dataclass
class HighlightCandidate:
    start: float
    end: float
    score: float
    title: str
    segment_indices: List[int] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class HighlightDetector:
    """
    Analiza segmentos de Whisper y selecciona los mejores momentos
    para clips de redes sociales (20–60 s).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.min_duration = settings.clip_min_duration
        self.max_duration = settings.clip_max_duration
        self.max_clips = settings.max_clips_per_video

    def detect(
        self,
        segments: Sequence[WhisperSegment],
        *,
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        max_clips: Optional[int] = None,
    ) -> List[HighlightCandidate]:
        if not segments:
            logger.warning("Sin segmentos para analizar highlights")
            return []

        # Permitir overrides por request sin mutar el singleton
        prev = (self.min_duration, self.max_duration, self.max_clips)
        self.min_duration = min_duration if min_duration is not None else prev[0]
        self.max_duration = max_duration if max_duration is not None else prev[1]
        self.max_clips = max_clips if max_clips is not None else prev[2]

        try:
            scored = [self._score_segment(seg, idx, segments) for idx, seg in enumerate(segments)]
            windows = self._build_windows(segments, scored)
            windows.sort(key=lambda w: w.score, reverse=True)
            selected = self._select_non_overlapping(windows)
            logger.info(
                "Highlights detectados: %d candidatos → %d seleccionados",
                len(windows),
                len(selected),
            )
            return selected
        finally:
            self.min_duration, self.max_duration, self.max_clips = prev

    def _score_segment(
        self,
        seg: WhisperSegment,
        idx: int,
        all_segments: Sequence[WhisperSegment],
    ) -> Dict[str, float]:
        text = seg.text.lower()
        reasons_score = 0.0
        details: Dict[str, float] = {}

        # Intensidad del habla (palabras por segundo)
        words = len(text.split())
        wps = words / seg.duration if seg.duration > 0.1 else 0
        speech_intensity = min(wps / 3.0, 2.0)  # ~3 wps = intensidad media
        details["speech_intensity"] = speech_intensity
        reasons_score += speech_intensity

        # Duración de frase (frases de 2–8 s suelen ser buenas)
        if 2.0 <= seg.duration <= 8.0:
            duration_score = 1.0
        elif seg.duration < 1.0:
            duration_score = 0.2
        else:
            duration_score = 0.6
        details["phrase_duration"] = duration_score
        reasons_score += duration_score

        # Palabras clave
        kw_score = 0.0
        for word, weight in KEYWORD_WEIGHTS.items():
            if re.search(rf"\b{re.escape(word)}\b", text):
                kw_score += weight
        kw_score = min(kw_score, 4.0)
        details["keywords"] = kw_score
        reasons_score += kw_score

        # Emociones / puntuación expresiva
        emotion_score = 0.0
        for pattern, weight in EMOTION_PATTERNS:
            if pattern.search(seg.text):
                emotion_score += weight
        emotion_score = min(emotion_score, 3.0)
        details["emotion"] = emotion_score
        reasons_score += emotion_score

        # Confianza Whisper (avg_logprob más alto = mejor)
        confidence = max(0.0, min(1.0, (seg.avg_logprob + 1.0)))  # ~[-1,0] → [0,1]
        no_speech_penalty = seg.no_speech_prob
        details["confidence"] = confidence - no_speech_penalty
        reasons_score += confidence - no_speech_penalty

        # Cambio de tema / pausa larga respecto al anterior
        if idx > 0:
            gap = seg.start - all_segments[idx - 1].end
            if gap >= 1.5:
                details["long_pause"] = 1.2
                reasons_score += 1.2
            # Jaccard simple de vocabulario → cambio de tema
            prev_words = set(all_segments[idx - 1].text.lower().split())
            curr_words = set(text.split())
            if prev_words and curr_words:
                overlap = len(prev_words & curr_words) / len(prev_words | curr_words)
                if overlap < 0.15:
                    details["topic_change"] = 1.0
                    reasons_score += 1.0

        return details | {"total": reasons_score}

    def _build_windows(
        self,
        segments: Sequence[WhisperSegment],
        scores: List[Dict[str, float]],
    ) -> List[HighlightCandidate]:
        """Agrupa segmentos contiguos en ventanas de 20–60 s sin cortar frases."""
        windows: List[HighlightCandidate] = []
        n = len(segments)

        for i in range(n):
            end_idx = i
            while end_idx < n:
                duration = segments[end_idx].end - segments[i].start
                if duration > self.max_duration:
                    break
                if duration >= self.min_duration:
                    window_scores = scores[i : end_idx + 1]
                    total = sum(s["total"] for s in window_scores)
                    # Bonus por cobertura de palabras
                    text_parts = [segments[j].text.strip() for j in range(i, end_idx + 1)]
                    joined = " ".join(text_parts)
                    word_bonus = min(len(joined.split()) / 40.0, 2.0)
                    score = (total / max(1, end_idx - i + 1)) + word_bonus

                    # Preferir duración ~30–45 s
                    ideal = 35.0
                    duration_fit = 1.0 - abs(duration - ideal) / ideal
                    score += max(0.0, duration_fit)

                    title = self._generate_title(joined)
                    reasons = self._summarize_reasons(window_scores)

                    windows.append(
                        HighlightCandidate(
                            start=segments[i].start,
                            end=segments[end_idx].end,
                            score=round(score, 3),
                            title=title,
                            segment_indices=list(range(i, end_idx + 1)),
                            reasons=reasons,
                        )
                    )
                end_idx += 1

        # Fallback: si el video es corto, crear una ventana con todo
        if not windows and segments:
            total_dur = segments[-1].end - segments[0].start
            if total_dur >= 5.0:
                joined = " ".join(s.text.strip() for s in segments)
                windows.append(
                    HighlightCandidate(
                        start=segments[0].start,
                        end=min(segments[-1].end, segments[0].start + self.max_duration),
                        score=1.0,
                        title=self._generate_title(joined),
                        segment_indices=list(range(len(segments))),
                        reasons=["fallback_full"],
                    )
                )
        return windows

    def _select_non_overlapping(
        self,
        candidates: List[HighlightCandidate],
        overlap_threshold: float = 0.4,
    ) -> List[HighlightCandidate]:
        selected: List[HighlightCandidate] = []
        for cand in candidates:
            if len(selected) >= self.max_clips:
                break
            if all(self._overlap_ratio(cand, s) < overlap_threshold for s in selected):
                selected.append(cand)
        selected.sort(key=lambda c: c.start)
        return selected

    @staticmethod
    def _overlap_ratio(a: HighlightCandidate, b: HighlightCandidate) -> float:
        inter_start = max(a.start, b.start)
        inter_end = min(a.end, b.end)
        inter = max(0.0, inter_end - inter_start)
        shorter = min(a.duration, b.duration) or 1.0
        return inter / shorter

    @staticmethod
    def _generate_title(text: str, max_words: int = 8) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return "Momento destacado"
        words = clean.split()
        title = " ".join(words[:max_words])
        if len(words) > max_words:
            title += "…"
        return title[:120].capitalize()

    @staticmethod
    def _summarize_reasons(window_scores: List[Dict[str, float]]) -> List[str]:
        keys = ("keywords", "emotion", "speech_intensity", "long_pause", "topic_change")
        averages = {
            k: sum(s.get(k, 0.0) for s in window_scores) / max(1, len(window_scores))
            for k in keys
        }
        ranked = sorted(averages.items(), key=lambda x: x[1], reverse=True)
        return [k for k, v in ranked if v > 0.3][:3]
