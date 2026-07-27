"""Opciones de procesamiento de video / clips."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ContentMode(str, Enum):
    """Tipo de contenido del video."""

    MONOLOGUE = "monologue"
    INTERVIEW = "interview"
    MULTI_SPEAKER = "multi_speaker"


class ClipFormat(str, Enum):
    """Formatos de salida para redes."""

    VERTICAL_9_16 = "vertical_9_16"
    PORTRAIT_4_5 = "portrait_4_5"
    SQUARE_1_1 = "square_1_1"
    LANDSCAPE_16_9 = "landscape_16_9"


class FillMode(str, Enum):
    SMART_CROP = "smart_crop"
    BLUR_BG = "blur_bg"
    LETTERBOX = "letterbox"


class SubtitleStyle(str, Enum):
    """Estilos visuales de subtítulos incrustados."""

    CLEAN = "clean"  # Contorno fino, sin caja (recomendado)
    SOCIAL = "social"  # Negrita redes, contorno fuerte, sin caja
    KARAOKE = "karaoke"  # Palabra activa resaltada (interactivo)
    BOXED = "boxed"  # Con fondo (legado / máxima legibilidad)
    SUBTLE = "subtle"  # Pequeño, discreto abajo


class SubtitlePosition(str, Enum):
    BOTTOM = "bottom"
    CENTER = "center"
    TOP = "top"


class InterviewLayout(str, Enum):
    SPLIT_STACK = "split_stack"
    ACTIVE_FOCUS = "active_focus"
    SINGLE_FOLLOW = "single_follow"


class ProcessingMode(str, Enum):
    """Cómo generar segmentos del video."""

    HIGHLIGHTS = "highlights"  # IA: mejores momentos
    FULL_SPLIT = "full_split"  # Dividir todo el video en partes


class SplitStrategy(str, Enum):
    """Estrategia de división en modo full_split."""

    BY_COUNT = "by_count"  # N partes iguales
    BY_DURATION = "by_duration"  # Partes de X segundos


FORMAT_RESOLUTIONS: dict[ClipFormat, tuple[int, int]] = {
    ClipFormat.VERTICAL_9_16: (1080, 1920),
    ClipFormat.PORTRAIT_4_5: (1080, 1350),
    ClipFormat.SQUARE_1_1: (1080, 1080),
    ClipFormat.LANDSCAPE_16_9: (1920, 1080),
}


class ProcessOptions(BaseModel):
    """Parámetros enviados al iniciar el procesamiento."""

    processing_mode: ProcessingMode = ProcessingMode.HIGHLIGHTS
    split_strategy: SplitStrategy = SplitStrategy.BY_DURATION
    split_part_count: int = Field(default=4, ge=2, le=50)
    split_part_duration: float = Field(default=60.0, ge=10.0, le=600.0)
    mirror_horizontal: bool = False

    content_mode: ContentMode = ContentMode.MONOLOGUE
    formats: List[ClipFormat] = Field(
        default_factory=lambda: [ClipFormat.VERTICAL_9_16],
        min_length=1,
    )
    fill_mode: FillMode = FillMode.SMART_CROP
    interview_layout: InterviewLayout = InterviewLayout.SPLIT_STACK

    burn_subtitles: bool = True
    subtitle_style: SubtitleStyle = SubtitleStyle.CLEAN
    subtitle_position: SubtitlePosition = SubtitlePosition.CENTER
    subtitle_size: int = Field(
        default=24,
        ge=12,
        le=48,
        description="Tamaño relativo (12–48). Se escala a la resolución del formato.",
    )
    export_srt: bool = True
    export_vtt: bool = True

    max_clips: int = Field(default=6, ge=1, le=20)
    min_clip_duration: float = Field(default=20.0, ge=5.0, le=120.0)
    max_clip_duration: float = Field(default=60.0, ge=10.0, le=180.0)

    language: Optional[str] = Field(default=None)

    @field_validator("subtitle_style", mode="before")
    @classmethod
    def migrate_old_styles(cls, v):
        legacy = {
            "default": SubtitleStyle.CLEAN,
            "large": SubtitleStyle.SOCIAL,
            "minimal": SubtitleStyle.SUBTLE,
        }
        if isinstance(v, str) and v in legacy:
            return legacy[v]
        return v

    @field_validator("formats")
    @classmethod
    def unique_formats(cls, v: List[ClipFormat]) -> List[ClipFormat]:
        seen: list[ClipFormat] = []
        for f in v:
            if f not in seen:
                seen.append(f)
        return seen

    @field_validator("max_clip_duration")
    @classmethod
    def max_gt_min(cls, v: float, info) -> float:
        min_d = info.data.get("min_clip_duration", 20.0)
        if v < min_d:
            raise ValueError("max_clip_duration debe ser >= min_clip_duration")
        return v


class ProcessOptionsRead(ProcessOptions):
    """Opciones guardadas / por defecto para la UI."""
