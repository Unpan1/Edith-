"""Servicio Whisper local para transcripción con timestamps."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import Settings
from app.utils.exceptions import WhisperNotAvailableError
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WhisperSegment:
    id: int
    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    words: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text.strip(),
            "avg_logprob": self.avg_logprob,
            "no_speech_prob": self.no_speech_prob,
            "words": self.words,
        }


@dataclass
class TranscriptionResult:
    text: str
    language: str
    segments: List[WhisperSegment]

    def segments_as_dicts(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.segments]


class WhisperService:
    """Carga y ejecuta un modelo Whisper local (openai-whisper)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.whisper_model
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise WhisperNotAvailableError(
                "El paquete openai-whisper no está instalado. Ejecuta: pip install openai-whisper"
            ) from exc

        try:
            logger.info("Cargando modelo Whisper '%s'...", self.model_name)
            start = time.perf_counter()
            self._model = whisper.load_model(self.model_name)
            logger.info("Modelo Whisper cargado en %.2fs", time.perf_counter() - start)
            return self._model
        except Exception as exc:  # noqa: BLE001
            raise WhisperNotAvailableError(f"No se pudo cargar Whisper: {exc}") from exc

    def transcribe(self, audio_path: str | Path, language: Optional[str] = None) -> TranscriptionResult:
        """Transcribe audio y retorna texto + segmentos con timestamps."""
        path = Path(audio_path)
        if not path.exists():
            raise WhisperNotAvailableError(f"Audio no encontrado: {path}")

        model = self._load_model()
        logger.info("Iniciando transcripción Whisper: %s", path)
        start = time.perf_counter()

        options: Dict[str, Any] = {
            "task": "transcribe",
            "verbose": False,
            "word_timestamps": True,
            "condition_on_previous_text": True,
        }
        if language:
            options["language"] = language

        try:
            result = model.transcribe(str(path), **options)
        except Exception as exc:  # noqa: BLE001
            raise WhisperNotAvailableError(f"Error durante la transcripción: {exc}") from exc

        elapsed = time.perf_counter() - start
        segments = [
            WhisperSegment(
                id=int(seg.get("id", idx)),
                start=float(seg.get("start", 0)),
                end=float(seg.get("end", 0)),
                text=str(seg.get("text", "")).strip(),
                avg_logprob=float(seg.get("avg_logprob") or 0.0),
                no_speech_prob=float(seg.get("no_speech_prob") or 0.0),
                words=list(seg.get("words") or []),
            )
            for idx, seg in enumerate(result.get("segments") or [])
            if str(seg.get("text", "")).strip()
        ]

        text = str(result.get("text") or "").strip()
        lang = str(result.get("language") or language or "unknown")
        logger.info(
            "Transcripción completada en %.2fs | idioma=%s | segmentos=%d | chars=%d",
            elapsed,
            lang,
            len(segments),
            len(text),
        )
        return TranscriptionResult(text=text, language=lang, segments=segments)
