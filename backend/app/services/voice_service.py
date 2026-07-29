"""TTS local/gratis con edge-tts (voces Microsoft Edge, sin API de pago)."""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.config.settings import Settings
from app.utils.exceptions import AppError, InvalidFileError, JobCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)

CancelCb = Callable[[], bool]
ProgressCb = Callable[[int, str, Optional[int]], None]

# Voces curadas: 20 español + 10 inglés (ShortName de edge-tts).
CURATED_VOICES = [
    # —— Español (20) ——
    {"id": "es-MX-DaliaNeural", "name": "Dalia", "locale": "es-MX", "gender": "Female", "style": "Cálida · México"},
    {"id": "es-MX-JorgeNeural", "name": "Jorge", "locale": "es-MX", "gender": "Male", "style": "Profesional · México"},
    {"id": "es-ES-ElviraNeural", "name": "Elvira", "locale": "es-ES", "gender": "Female", "style": "Clara · España"},
    {"id": "es-ES-AlvaroNeural", "name": "Álvaro", "locale": "es-ES", "gender": "Male", "style": "Natural · España"},
    {"id": "es-ES-XimenaNeural", "name": "Ximena", "locale": "es-ES", "gender": "Female", "style": "Moderna · España"},
    {"id": "es-AR-ElenaNeural", "name": "Elena", "locale": "es-AR", "gender": "Female", "style": "Argentina"},
    {"id": "es-AR-TomasNeural", "name": "Tomás", "locale": "es-AR", "gender": "Male", "style": "Argentina"},
    {"id": "es-CO-SalomeNeural", "name": "Salomé", "locale": "es-CO", "gender": "Female", "style": "Colombia"},
    {"id": "es-CO-GonzaloNeural", "name": "Gonzalo", "locale": "es-CO", "gender": "Male", "style": "Colombia"},
    {"id": "es-US-PalomaNeural", "name": "Paloma", "locale": "es-US", "gender": "Female", "style": "EE.UU. (español)"},
    {"id": "es-US-AlonsoNeural", "name": "Alonso", "locale": "es-US", "gender": "Male", "style": "EE.UU. (español)"},
    {"id": "es-PE-CamilaNeural", "name": "Camila", "locale": "es-PE", "gender": "Female", "style": "Perú"},
    {"id": "es-PE-AlexNeural", "name": "Alex", "locale": "es-PE", "gender": "Male", "style": "Perú"},
    {"id": "es-CL-CatalinaNeural", "name": "Catalina", "locale": "es-CL", "gender": "Female", "style": "Chile"},
    {"id": "es-CL-LorenzoNeural", "name": "Lorenzo", "locale": "es-CL", "gender": "Male", "style": "Chile"},
    {"id": "es-VE-PaolaNeural", "name": "Paola", "locale": "es-VE", "gender": "Female", "style": "Venezuela"},
    {"id": "es-VE-SebastianNeural", "name": "Sebastián", "locale": "es-VE", "gender": "Male", "style": "Venezuela"},
    {"id": "es-UY-ValentinaNeural", "name": "Valentina", "locale": "es-UY", "gender": "Female", "style": "Uruguay"},
    {"id": "es-CR-MariaNeural", "name": "María", "locale": "es-CR", "gender": "Female", "style": "Costa Rica"},
    {"id": "es-EC-LuisNeural", "name": "Luis", "locale": "es-EC", "gender": "Male", "style": "Ecuador"},
    # —— English (10) ——
    {"id": "en-US-JennyNeural", "name": "Jenny", "locale": "en-US", "gender": "Female", "style": "English · US"},
    {"id": "en-US-GuyNeural", "name": "Guy", "locale": "en-US", "gender": "Male", "style": "English · US"},
    {"id": "en-US-AriaNeural", "name": "Aria", "locale": "en-US", "gender": "Female", "style": "English · US"},
    {"id": "en-US-DavisNeural", "name": "Davis", "locale": "en-US", "gender": "Male", "style": "English · US"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "locale": "en-GB", "gender": "Female", "style": "English · UK"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "locale": "en-GB", "gender": "Male", "style": "English · UK"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha", "locale": "en-AU", "gender": "Female", "style": "English · Australia"},
    {"id": "en-AU-WilliamNeural", "name": "William", "locale": "en-AU", "gender": "Male", "style": "English · Australia"},
    {"id": "en-CA-ClaraNeural", "name": "Clara", "locale": "en-CA", "gender": "Female", "style": "English · Canada"},
    {"id": "en-CA-LiamNeural", "name": "Liam", "locale": "en-CA", "gender": "Male", "style": "English · Canada"},
]

# Modos vía rate/pitch/volume nativos de edge-tts.
# Valores más extremos para que se note bien la diferencia.
SPEECH_MOODS: Dict[str, Dict[str, Any]] = {
    "neutral": {
        "label": "Neutral",
        "rate": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "post_tempo": 1.0,
        "post_volume": 1.0,
        "post_pitch": 1.0,
    },
    "nervous": {
        "label": "Nervioso",
        "rate": "+35%",
        "pitch": "+18Hz",
        "volume": "+5%",
        "post_tempo": 1.12,
        "post_volume": 1.05,
        "post_pitch": 1.06,
    },
    "anxious": {
        "label": "Ansioso",
        "rate": "+25%",
        "pitch": "+12Hz",
        "volume": "-8%",
        "post_tempo": 1.08,
        "post_volume": 0.95,
        "post_pitch": 1.04,
    },
    "furious": {
        "label": "Furioso",
        "rate": "+18%",
        "pitch": "-14Hz",
        "volume": "+45%",
        "post_tempo": 1.06,
        "post_volume": 1.55,
        "post_pitch": 0.94,
    },
    "shouting": {
        "label": "Gritando",
        "rate": "+40%",
        "pitch": "+22Hz",
        "volume": "+70%",
        "post_tempo": 1.15,
        "post_volume": 1.85,
        "post_pitch": 1.08,
    },
    "sad": {
        "label": "Triste",
        "rate": "-35%",
        "pitch": "-18Hz",
        "volume": "-30%",
        "post_tempo": 0.82,
        "post_volume": 0.72,
        "post_pitch": 0.92,
    },
    "cheerful": {
        "label": "Alegre",
        "rate": "+22%",
        "pitch": "+14Hz",
        "volume": "+20%",
        "post_tempo": 1.08,
        "post_volume": 1.15,
        "post_pitch": 1.05,
    },
    "whisper": {
        "label": "Susurrando",
        "rate": "-22%",
        "pitch": "-10Hz",
        "volume": "-55%",
        "post_tempo": 0.9,
        "post_volume": 0.45,
        "post_pitch": 0.96,
    },
}


@dataclass
class VoiceSynthResult:
    path: Path
    voice_id: str
    filename: str
    size_bytes: int
    mood: str = "neutral"


class VoiceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.voices_dir = Path(settings.output_folder) / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)

    def list_voices(self) -> List[dict]:
        return list(CURATED_VOICES)

    def list_moods(self) -> List[dict]:
        return [
            {"id": k, "label": v["label"], "rate": v["rate"], "pitch": v["pitch"]}
            for k, v in SPEECH_MOODS.items()
        ]

    def _validate_text(self, text: str, max_len: int = 20000) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            raise InvalidFileError("Escribe un texto para narrar")
        if len(cleaned) > max_len:
            raise InvalidFileError(f"Máximo {max_len} caracteres por bloque")
        return cleaned

    def _validate_voice(self, voice_id: str) -> str:
        ids = {v["id"] for v in CURATED_VOICES}
        if voice_id not in ids:
            raise InvalidFileError("Voz no válida. Elige una de la lista.")
        return voice_id

    def _mood_params(
        self,
        mood: str,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        speed: int = 0,
    ) -> Dict[str, Any]:
        base = SPEECH_MOODS.get(mood) or SPEECH_MOODS["neutral"]
        out = dict(base)
        # Solo override si el cliente manda un valor explícito (no defaults vacíos).
        if rate and rate.strip() and re.match(r"^[+-]\d+%$", rate.strip()):
            out["rate"] = rate.strip()
        if pitch and pitch.strip() and re.match(r"^[+-]\d+Hz$", pitch.strip()):
            out["pitch"] = pitch.strip()
        # Ajuste de velocidad del usuario (se suma al rate del mood)
        if speed:
            m = re.match(r"^([+-]?\d+)%$", str(out.get("rate") or "+0%"))
            base_rate = int(m.group(1)) if m else 0
            combined = max(-50, min(100, base_rate + int(speed)))
            out["rate"] = f"+{combined}%" if combined >= 0 else f"{combined}%"
            # Refuerzo leve de tempo en postproceso
            post = float(out.get("post_tempo") or 1.0)
            out["post_tempo"] = max(0.55, min(1.85, post * (1.0 + speed / 200.0)))
        return out

    def _apply_mood_postprocess(self, path: Path, params: Dict[str, Any]) -> None:
        """Refuerza el modo con FFmpeg (tempo/tono/volumen) para que se note claro."""
        tempo = float(params.get("post_tempo") or 1.0)
        vol = float(params.get("post_volume") or 1.0)
        pitch_f = float(params.get("post_pitch") or 1.0)
        if abs(tempo - 1.0) < 0.01 and abs(vol - 1.0) < 0.01 and abs(pitch_f - 1.0) < 0.01:
            return

        ffmpeg = self.settings.ffmpeg_path
        if not shutil.which(ffmpeg) and not Path(ffmpeg).exists():
            logger.warning("FFmpeg no disponible; se omitió postproceso de mood")
            return

        # atempo solo acepta 0.5–2.0; encadenar si hace falta
        tempo = max(0.5, min(2.0, tempo))
        pitch_f = max(0.85, min(1.2, pitch_f))
        filters: List[str] = []
        if abs(pitch_f - 1.0) >= 0.01:
            # Cambia tono y luego re-muestrea; atempo corrige la duración
            filters.append(f"asetrate=24000*{pitch_f:.4f},aresample=24000")
            fix_tempo = 1.0 / pitch_f
            tempo = max(0.5, min(2.0, tempo * fix_tempo))
        if abs(tempo - 1.0) >= 0.01:
            filters.append(f"atempo={tempo:.4f}")
        if abs(vol - 1.0) >= 0.01:
            filters.append(f"volume={vol:.3f}")
        if not filters:
            return

        tmp = path.with_suffix(".mood.mp3")
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(path),
                "-af",
                ",".join(filters),
                "-q:a",
                "4",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > 64:
            path.unlink(missing_ok=True)
            tmp.rename(path)
        else:
            tmp.unlink(missing_ok=True)
            logger.warning(
                "Postproceso mood falló: %s",
                (result.stderr or "")[-300:],
            )

    def _run_async(self, coro) -> None:
        try:
            asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()

    def synthesize(
        self,
        text: str,
        voice_id: str = "es-MX-DaliaNeural",
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        mood: str = "neutral",
        speed: int = 0,
        should_cancel: Optional[CancelCb] = None,
    ) -> VoiceSynthResult:
        try:
            import edge_tts  # type: ignore
        except ImportError as exc:
            raise AppError(
                "edge-tts no está instalado. Ejecuta: pip install edge-tts",
                status_code=500,
            ) from exc

        if should_cancel and should_cancel():
            raise JobCancelledError()

        cleaned = self._validate_text(text)
        voice = self._validate_voice(voice_id)
        mood_key = mood if mood in SPEECH_MOODS else "neutral"
        params = self._mood_params(mood_key, rate, pitch, speed=speed)

        out_name = f"voice_{uuid.uuid4().hex}.mp3"
        out_path = self.voices_dir / out_name

        async def _run() -> None:
            # Texto plano + rate/pitch/volume. edge-tts arma su propio SSML.
            communicate = edge_tts.Communicate(
                cleaned,
                voice,
                rate=params["rate"],
                pitch=params["pitch"],
                volume=params.get("volume") or "+0%",
            )
            await communicate.save(str(out_path))

        try:
            self._run_async(_run())
        except Exception as exc:  # noqa: BLE001
            logger.exception("edge-tts falló: %s", exc)
            out_path.unlink(missing_ok=True)
            raise AppError(
                f"No se pudo generar la voz: {str(exc)[:300]}"
            ) from exc

        if should_cancel and should_cancel():
            out_path.unlink(missing_ok=True)
            raise JobCancelledError()

        if not out_path.exists() or out_path.stat().st_size < 64:
            raise AppError("La generación de audio no produjo un archivo válido")

        needs_post = mood_key != "neutral" or abs(float(params.get("post_tempo") or 1.0) - 1.0) >= 0.01
        if needs_post:
            self._apply_mood_postprocess(out_path, params)

        if should_cancel and should_cancel():
            out_path.unlink(missing_ok=True)
            raise JobCancelledError()

        size = out_path.stat().st_size
        logger.info(
            "TTS %s mood=%s rate=%s speed=%s → %s (%.1f KB)",
            voice,
            mood_key,
            params["rate"],
            speed,
            out_name,
            size / 1024,
        )
        return VoiceSynthResult(
            path=out_path.resolve(),
            voice_id=voice,
            filename=out_name,
            size_bytes=size,
            mood=mood_key,
        )

    def synthesize_dialogue(
        self,
        turns: Sequence[Dict[str, Any]],
        *,
        pause_ms: int = 350,
        speed: int = 0,
        should_cancel: Optional[CancelCb] = None,
        on_progress: Optional[ProgressCb] = None,
    ) -> VoiceSynthResult:
        """Genera un solo MP3 con varias voces / personajes en secuencia."""
        if not turns:
            raise InvalidFileError("Agrega al menos un turno de diálogo")
        if len(turns) > 40:
            raise InvalidFileError("Máximo 40 turnos por diálogo")

        total_chars = sum(len((t.get("text") or "").strip()) for t in turns)
        if total_chars > 20000:
            raise InvalidFileError("El diálogo supera 20000 caracteres en total")

        pause_ms = max(80, min(2000, int(pause_ms)))
        part_paths: List[Path] = []
        work = self.voices_dir / f"_dlg_{uuid.uuid4().hex}"
        work.mkdir(parents=True, exist_ok=True)

        def check() -> None:
            if should_cancel and should_cancel():
                raise JobCancelledError()

        try:
            n = len(turns)
            for i, turn in enumerate(turns):
                check()
                if on_progress:
                    on_progress(
                        5 + int(85 * i / max(n, 1)),
                        f"Turno {i + 1}/{n}…",
                        max(3, (n - i) * 4),
                    )
                text = self._validate_text(str(turn.get("text") or ""), max_len=3000)
                voice_id = self._validate_voice(str(turn.get("voice_id") or ""))
                mood = str(turn.get("mood") or "neutral")
                turn_speed = turn.get("speed")
                if turn_speed is None:
                    turn_speed = speed
                part = self.synthesize(
                    text=text,
                    voice_id=voice_id,
                    mood=mood,
                    rate=turn.get("rate") or None,
                    pitch=turn.get("pitch") or None,
                    speed=int(turn_speed or 0),
                    should_cancel=should_cancel,
                )
                # Mover a carpeta de trabajo con nombre ordenado
                dest = work / f"part_{i:03d}.mp3"
                shutil.move(str(part.path), str(dest))
                part_paths.append(dest)

            check()
            if on_progress:
                on_progress(92, "Uniendo turnos…", 3)
            out_name = f"voice_{uuid.uuid4().hex}.mp3"
            out_path = self.voices_dir / out_name
            self._concat_mp3(part_paths, out_path, pause_ms=pause_ms)

            check()
            size = out_path.stat().st_size
            logger.info(
                "Diálogo TTS %d turnos → %s (%.1f KB)",
                len(part_paths),
                out_name,
                size / 1024,
            )
            if on_progress:
                on_progress(100, "Diálogo listo", None)
            return VoiceSynthResult(
                path=out_path.resolve(),
                voice_id="dialogue",
                filename=out_name,
                size_bytes=size,
                mood="dialogue",
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _concat_mp3(
        self, parts: List[Path], output: Path, *, pause_ms: int = 350
    ) -> None:
        """Concatena MP3 con silencio entre turnos vía FFmpeg."""
        ffmpeg = self.settings.ffmpeg_path
        if not shutil.which(ffmpeg) and not Path(ffmpeg).exists():
            raise AppError("FFmpeg no encontrado para unir el diálogo", status_code=500)

        # Generar silencio corto
        silence = parts[0].parent / "silence.mp3"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=24000:cl=mono",
                "-t",
                f"{pause_ms / 1000.0:.3f}",
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(silence),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        list_file = parts[0].parent / "concat.txt"
        lines: List[str] = []
        for i, p in enumerate(parts):
            safe = str(p.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
            if i < len(parts) - 1 and silence.exists():
                ssafe = str(silence.resolve()).replace("\\", "/").replace("'", "'\\''")
                lines.append(f"file '{ssafe}'")
        list_file.write_text("\n".join(lines), encoding="utf-8")

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.exists():
            # Re-encode si copy falla (codecs distintos)
            result2 = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "4",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result2.returncode != 0 or not output.exists():
                err = (result2.stderr or result.stderr or "")[-400:]
                raise AppError(f"No se pudo unir el diálogo: {err}")

    def resolve_file(self, filename: str) -> Path:
        safe = Path(filename).name
        if not re.match(r"^voice_[a-f0-9]+\.mp3$", safe):
            raise AppError("Archivo de voz inválido", status_code=400)
        path = (self.voices_dir / safe).resolve()
        if not str(path).startswith(str(self.voices_dir.resolve())):
            raise AppError("Ruta no permitida", status_code=400)
        if not path.exists():
            raise AppError("Audio no encontrado", status_code=404)
        return path
