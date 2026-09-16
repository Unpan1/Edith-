"""Extracción de texto de YouTube / Instagram / Facebook (subtítulos o Whisper)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from app.ai.speaker_diarization import assign_speakers, format_dialogue
from app.ai.text_cleanup import cleanup_transcript_text
from app.config.settings import Settings
from app.utils.exceptions import AppError
from app.utils.logger import get_logger
from app.video.youtube_service import YoutubeService, yt_dlp_base_opts

logger = get_logger(__name__)

ProgressCb = Callable[[int, str, Optional[int]], None]


@dataclass
class TranscriptCue:
    start: float
    end: float
    text: str
    speaker: int = 1


@dataclass
class YoutubeTranscriptResult:
    title: str
    url: str
    language: Optional[str]
    source: str  # captions | auto_captions | whisper
    text: str
    cues: List[TranscriptCue] = field(default_factory=list)
    duration: Optional[float] = None
    speakers_count: int = 1
    platform: str = "youtube"


def _strip_vtt(content: str) -> List[TranscriptCue]:
    """Parsea VTT/SRT simple a cues de texto."""
    # Quitar header WEBVTT y NOTE
    content = content.replace("\ufeff", "")
    blocks = re.split(r"\n\s*\n", content.strip())
    cues: List[TranscriptCue] = []
    time_re = re.compile(
        r"(\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3}\s*-->\s*(\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3}"
    )

    def _to_sec(ts: str) -> float:
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
        else:
            h, m, s = "0", parts[0], parts[1]
        return int(h) * 3600 + int(m) * 60 + float(s)

    seen_texts: set[str] = set()
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        # Saltar WEBVTT / NOTE / índices numéricos
        if lines[0].upper().startswith("WEBVTT") or lines[0].upper().startswith("NOTE"):
            continue
        time_line = None
        text_lines: List[str] = []
        for ln in lines:
            if "-->" in ln:
                time_line = ln
            elif time_line and not re.fullmatch(r"\d+", ln):
                # Quitar tags VTT <c> etc.
                clean = re.sub(r"<[^>]+>", "", ln).strip()
                if clean:
                    text_lines.append(clean)
        if not time_line or not text_lines:
            continue
        m = re.match(
            r"((?:\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3})",
            time_line,
        )
        if not m:
            continue
        text = " ".join(text_lines)
        # Evitar duplicados típicos de auto-captions solapadas
        key = text.lower()
        if key in seen_texts:
            continue
        seen_texts.add(key)
        cues.append(
            TranscriptCue(start=_to_sec(m.group(1)), end=_to_sec(m.group(2)), text=text)
        )
    return cues


def _cues_to_text(cues: List[TranscriptCue]) -> str:
    if not cues:
        return ""
    # Unir en párrafos cada ~25s o cambio natural
    parts: List[str] = []
    buf: List[str] = []
    last_end = cues[0].start
    for c in cues:
        if buf and (c.start - last_end > 8 or len(" ".join(buf)) > 280):
            parts.append(" ".join(buf))
            buf = []
        buf.append(c.text)
        last_end = c.end
    if buf:
        parts.append(" ".join(buf))
    return "\n\n".join(parts).strip()


class YoutubeTranscriptService:
    def __init__(self, settings: Settings, whisper=None, ffmpeg=None):
        self.settings = settings
        self.youtube = YoutubeService(settings)
        self.whisper = whisper
        self.ffmpeg = ffmpeg
        self.work_dir = Path(settings.temp_folder) / "yt_transcripts"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def extract(
        self,
        url: str,
        *,
        language: Optional[str] = None,
        prefer_whisper: bool = False,
        detect_speakers: bool = True,
        on_progress: Optional[ProgressCb] = None,
    ) -> YoutubeTranscriptResult:
        clean, platform = self.youtube.normalize_media_url(url)
        label = {
            "youtube": "YouTube",
            "instagram": "Instagram",
            "facebook": "Facebook",
        }.get(platform, platform)

        if on_progress:
            on_progress(5, f"Obteniendo información de {label}…", None)

        # Instagram / Facebook no suelen traer subtítulos útiles → Whisper
        use_captions = platform == "youtube" and not prefer_whisper
        if use_captions:
            try:
                result = self._from_captions(clean, language=language, on_progress=on_progress)
                if result and result.text.strip():
                    result.platform = platform
                    if detect_speakers:
                        result = self._attach_speakers_from_audio(
                            clean, result, on_progress=on_progress
                        )
                    return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("Subtítulos YouTube no disponibles: %s", exc)

        if on_progress:
            if platform == "youtube":
                on_progress(25, "Sin subtítulos útiles. Descargando audio para Whisper…", None)
            else:
                on_progress(25, f"Descargando audio de {label} para transcribir…", None)

        result = self._from_whisper(
            clean,
            language=language,
            detect_speakers=detect_speakers,
            on_progress=on_progress,
            platform=platform,
        )
        result.platform = platform
        return result

    def _from_captions(
        self,
        url: str,
        *,
        language: Optional[str],
        on_progress: Optional[ProgressCb],
    ) -> Optional[YoutubeTranscriptResult]:
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise AppError("yt-dlp no está instalado") from exc

        job_dir = self.work_dir / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)

        langs = []
        if language:
            langs.append(language)
        langs.extend(["es", "es-419", "es-ES", "es-MX", "en", "en-US", "en-GB"])
        # únicos
        seen = set()
        lang_list = [x for x in langs if not (x in seen or seen.add(x))]

        ydl_opts = {
            **yt_dlp_base_opts(platform="youtube"),
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": lang_list,
            "subtitlesformat": "vtt",
            "outtmpl": str(job_dir / "%(id)s.%(ext)s"),
        }

        if on_progress:
            on_progress(15, "Buscando subtítulos de YouTube…", None)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
            if "entries" in info and info["entries"]:
                info = info["entries"][0]
            title = (info.get("title") or "YouTube").strip()
            duration = info.get("duration")
            vid = info.get("id") or "video"

        # Preferir manual > auto
        vtt_files = sorted(job_dir.glob("*.vtt"))
        if not vtt_files:
            # a veces extensión .es.vtt etc.
            vtt_files = list(job_dir.glob("*.*.vtt"))
        if not vtt_files:
            self._cleanup(job_dir)
            return None

        # Orden: idioma pedido, luego es, luego en, luego cualquiera
        def score(p: Path) -> int:
            name = p.name.lower()
            s = 0
            if language and f".{language.lower()}" in name:
                s += 100
            if ".es" in name:
                s += 50
            if ".en" in name:
                s += 20
            # manual suele no llevar "auto"; yt-dlp no siempre distingue en nombre
            return s

        vtt_files.sort(key=score, reverse=True)
        chosen = vtt_files[0]
        content = chosen.read_text(encoding="utf-8", errors="ignore")
        cues = _strip_vtt(content)
        text = _cues_to_text(cues)
        if not text:
            # fallback: texto crudo sin timestamps
            text = re.sub(r"<[^>]+>", "", content)
            text = re.sub(r"WEBVTT|NOTE.*", "", text)
            text = re.sub(
                r"(\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3}\s*-->\s*(\d{1,2}:)?\d{2}:\d{2}[\.,]\d{3}",
                "",
                text,
            )
            text = re.sub(r"\n{2,}", "\n", text).strip()

        lang_guess = None
        m = re.search(r"\.([a-z]{2}(?:-[A-Za-z0-9]+)?)\.vtt$", chosen.name, re.I)
        if m:
            lang_guess = m.group(1)

        source = "auto_captions"
        # Si hay subtítulos manuales en info
        subs = info.get("subtitles") or {}
        if any(lang_guess and lang_guess.startswith(k[:2]) for k in subs.keys()):
            source = "captions"

        text = cleanup_transcript_text(text, lang_guess or language)
        for c in cues:
            c.text = cleanup_transcript_text(c.text, lang_guess or language)

        if on_progress:
            on_progress(70, "Texto extraído de subtítulos de YouTube", None)

        self._cleanup(job_dir)
        return YoutubeTranscriptResult(
            title=title,
            url=url,
            language=lang_guess or language,
            source=source,
            text=text,
            cues=cues,
            duration=float(duration) if duration else None,
            speakers_count=1,
        )

    def _from_whisper(
        self,
        url: str,
        *,
        language: Optional[str],
        detect_speakers: bool = True,
        on_progress: Optional[ProgressCb],
        platform: str = "youtube",
    ) -> YoutubeTranscriptResult:
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise AppError("yt-dlp no está instalado") from exc

        if self.whisper is None:
            raise AppError(
                "Whisper no está disponible para transcribir sin subtítulos",
                status_code=500,
            )

        label = {
            "youtube": "YouTube",
            "instagram": "Instagram",
            "facebook": "Facebook",
        }.get(platform, platform)

        job_dir = self.work_dir / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(job_dir / "%(id)s.%(ext)s")

        ydl_opts = {
            **yt_dlp_base_opts(platform=platform),
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
        }
        ffmpeg_parent = Path(self.settings.ffmpeg_path).parent
        if ffmpeg_parent.exists():
            ydl_opts["ffmpeg_location"] = str(ffmpeg_parent)

        if on_progress:
            on_progress(35, f"Descargando audio de {label}…", None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise AppError(f"No se pudo obtener el video de {label}")
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                title = (info.get("title") or info.get("id") or label).strip()
                duration = info.get("duration")
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            logger.exception("Error audio yt-dlp (%s): %s", label, exc)
            if "private" in msg:
                raise AppError(f"El video de {label} es privado o no accesible") from exc
            if "login" in msg or "sign in" in msg or "cookie" in msg:
                raise AppError(
                    f"{label} pidió inicio de sesión. Usa un Reel/video público."
                ) from exc
            if "unavailable" in msg or "not available" in msg:
                raise AppError(f"El video de {label} no está disponible") from exc
            raise AppError(f"No se pudo descargar audio de {label}: {exc}") from exc

        audio_files = list(job_dir.glob("*.wav")) + list(job_dir.glob("*.m4a")) + list(job_dir.glob("*.webm"))
        if not audio_files:
            raise AppError(f"No se pudo descargar el audio de {label}")
        audio_path = audio_files[0]

        if audio_path.suffix.lower() != ".wav" and self.ffmpeg:
            wav = job_dir / f"{audio_path.stem}.wav"
            try:
                self.ffmpeg.extract_audio(audio_path, wav)
                audio_path = wav
            except Exception as exc:  # noqa: BLE001
                logger.warning("Conversión audio: %s", exc)

        if on_progress:
            on_progress(55, "Transcribiendo con Whisper (mejor calidad)…", None)

        # Español por defecto si no se indica (reduce confusiones de idioma)
        lang = language or "es"
        result = self.whisper.transcribe(audio_path, language=lang, high_quality=True)
        cues = [
            TranscriptCue(start=s.start, end=s.end, text=s.text.strip(), speaker=1)
            for s in result.segments
            if (s.text or "").strip()
        ]

        speakers_count = 1
        if detect_speakers and cues and audio_path.suffix.lower() == ".wav":
            if on_progress:
                on_progress(88, "Detectando si hay distintos hablantes…", None)
            speakers, speakers_count = assign_speakers(
                audio_path,
                [(c.start, c.end) for c in cues],
            )
            for c, sp in zip(cues, speakers):
                c.speaker = sp

        if speakers_count > 1:
            text = format_dialogue(
                [c.text for c in cues],
                [c.speaker for c in cues],
            )
        else:
            text = cleanup_transcript_text(
                result.text.strip() or _cues_to_text(cues),
                result.language or lang,
            )

        if on_progress:
            detail = (
                f"Listo · {speakers_count} hablante(s) detectado(s)"
                if detect_speakers
                else "Transcripción Whisper completada"
            )
            on_progress(100, detail, None)

        self._cleanup(job_dir)
        return YoutubeTranscriptResult(
            title=title,
            url=url,
            language=result.language or lang,
            source="whisper",
            text=text,
            cues=cues,
            duration=float(duration) if duration else None,
            speakers_count=speakers_count,
            platform=platform,
        )

    def _attach_speakers_from_audio(
        self,
        url: str,
        result: YoutubeTranscriptResult,
        *,
        on_progress: Optional[ProgressCb],
    ) -> YoutubeTranscriptResult:
        """Descarga solo audio para etiquetar hablantes sobre subtítulos ya obtenidos."""
        if not result.cues or self.ffmpeg is None:
            return result
        try:
            import yt_dlp  # type: ignore
        except ImportError:
            return result

        if on_progress:
            on_progress(78, "Analizando audio para detectar hablantes…", None)

        job_dir = self.work_dir / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)
        try:
            ydl_opts = {
                **yt_dlp_base_opts(platform="youtube"),
                "format": "bestaudio/best",
                "outtmpl": str(job_dir / "%(id)s.%(ext)s"),
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                        "preferredquality": "192",
                    }
                ],
            }
            ffmpeg_parent = Path(self.settings.ffmpeg_path).parent
            if ffmpeg_parent.exists():
                ydl_opts["ffmpeg_location"] = str(ffmpeg_parent)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            wavs = list(job_dir.glob("*.wav"))
            if not wavs:
                return result
            audio_path = wavs[0]
            if self.ffmpeg and audio_path.stat().st_size > 0:
                # Re-sample a 16k mono por si el postprocessor no lo hizo
                mono = job_dir / "mono16.wav"
                try:
                    self.ffmpeg.extract_audio(audio_path, mono)
                    audio_path = mono
                except Exception:  # noqa: BLE001
                    pass

            speakers, n = assign_speakers(
                audio_path,
                [(c.start, c.end) for c in result.cues],
            )
            for c, sp in zip(result.cues, speakers):
                c.speaker = sp
            result.speakers_count = n
            if n > 1:
                result.text = format_dialogue(
                    [c.text for c in result.cues],
                    [c.speaker for c in result.cues],
                )
            if on_progress:
                on_progress(100, f"Listo · {n} hablante(s) detectado(s)", None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Diarización sobre subtítulos omitida: %s", exc)
            if on_progress:
                on_progress(100, "Texto listo (sin diarización)", None)
        finally:
            self._cleanup(job_dir)
        return result

    @staticmethod
    def _cleanup(path: Path) -> None:
        try:
            if path.is_dir():
                for p in path.rglob("*"):
                    if p.is_file():
                        p.unlink(missing_ok=True)
                path.rmdir()
        except OSError:
            pass
