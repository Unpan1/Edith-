"""Limpieza / corrección ligera de transcripciones (español)."""

from __future__ import annotations

import re
from typing import List


# Pares (patrón, reemplazo) — confusiones frecuentes ASR en español
_ES_FIXES = [
    (r"\bhalla\b", "haya"),
    (r"\bahy\b", "hay"),
    (r"\bhaber\b(?=\s+(?:que|de)\b)", "a ver"),  # a veces
    (r"\ba ver que\b", "a ver qué"),
    (r"\bpor que\b", "porque"),
    (r"\bPor que\b", "Porque"),
    (r"\basi que\b", "así que"),
    (r"\bmas o menos\b", "más o menos"),
    (r"\bmas\b(?=\s+(?:tarde|antes|bien|o)\b)", "más"),
    (r"\btambien\b", "también"),
    (r"\bTambien\b", "También"),
    (r"\bdespues\b", "después"),
    (r"\bDespues\b", "Después"),
    (r"\bquiza\b", "quizá"),
    (r"\bQuizas\b", "Quizás"),
    (r"\bquizás\b", "quizás"),
    (r"\binformacion\b", "información"),
    (r"\bcomunicacion\b", "comunicación"),
    (r"\bgrabacion\b", "grabación"),
    (r"\btranscripcion\b", "transcripción"),
    (r"\bvideo\b", "video"),  # keep
    (r"\bokey\b", "ok"),
    (r"\beh+\b", ""),  # muletillas sueltas
    (r"\beste+\b(?=\s|,|\.)", ""),
    (r"\s{2,}", " "),
    (r"\s+([,.!?…])", r"\1"),
]


def cleanup_transcript_text(text: str, language: str | None = None) -> str:
    if not text:
        return ""
    out = text.strip()
    lang = (language or "").lower()
    if lang.startswith("es") or lang in ("", "unknown"):
        for pat, repl in _ES_FIXES:
            out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    # Espaciado y mayúsculas tras punto
    out = re.sub(r"\s+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = _capitalize_sentences(out)
    return out.strip()


def cleanup_segment_texts(texts: List[str], language: str | None = None) -> List[str]:
    return [cleanup_transcript_text(t, language) for t in texts]


def _capitalize_sentences(text: str) -> str:
    parts = re.split(r"([.!?…]\s+)", text)
    rebuilt: List[str] = []
    cap_next = True
    for p in parts:
        if not p:
            continue
        if re.fullmatch(r"[.!?…]\s+", p):
            rebuilt.append(p)
            cap_next = True
            continue
        if cap_next and p[0].isalpha():
            rebuilt.append(p[0].upper() + p[1:])
        else:
            rebuilt.append(p)
        cap_next = False
    return "".join(rebuilt)


# Prompt inicial para Whisper en español (mejora coherencia / nombres comunes)
ES_INITIAL_PROMPT = (
    "Transcripción en español claro. Incluye signos de puntuación. "
    "Vocabulario: video, stream, chat, redes sociales, YouTube, podcast, entrevista."
)
