"""Generación de videos narrados a partir de historias (local / gratis)."""

from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.config.settings import Settings
from app.services.voice_service import VoiceService
from app.utils.exceptions import AppError, InvalidFileError, JobCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)

ProgressCb = Callable[[int, str, Optional[int]], None]
CancelCb = Callable[[], bool]

PRESETS: Dict[str, Dict[str, Any]] = {
    "narracion": {
        "label": "Narración",
        "description": "Relato claro, ritmo medio, visuales suaves",
        "bg": (18, 28, 48),
        "accent": (94, 234, 212),
        "text": (240, 248, 255),
        "muted": (148, 163, 184),
        "pause_ms": 380,
        "max_scenes": 12,
        "target_chars": 220,
    },
    "misterio": {
        "label": "Misterio",
        "description": "Atmósfera oscura, pausas largas, texto enigmático",
        "bg": (12, 10, 22),
        "accent": (167, 139, 250),
        "text": (226, 232, 240),
        "muted": (120, 113, 150),
        "pause_ms": 520,
        "max_scenes": 12,
        "target_chars": 200,
    },
    "motivacional": {
        "label": "Motivacional",
        "description": "Energía alta, frases cortas, contraste fuerte",
        "bg": (8, 47, 73),
        "accent": (251, 191, 36),
        "text": (255, 255, 255),
        "muted": (186, 230, 253),
        "pause_ms": 280,
        "max_scenes": 14,
        "target_chars": 160,
    },
    "terror": {
        "label": "Terror",
        "description": "Oscuro, lento, acentos rojos",
        "bg": (10, 6, 8),
        "accent": (248, 113, 113),
        "text": (254, 226, 226),
        "muted": (127, 29, 29),
        "pause_ms": 600,
        "max_scenes": 12,
        "target_chars": 180,
    },
    "documental": {
        "label": "Documental",
        "description": "Sobrio, tipografía limpia, ritmo estable",
        "bg": (24, 24, 27),
        "accent": (125, 211, 252),
        "text": (250, 250, 250),
        "muted": (161, 161, 170),
        "pause_ms": 350,
        "max_scenes": 12,
        "target_chars": 240,
    },
    "humor": {
        "label": "Humor",
        "description": "Colores vivos, ritmo ágil, frases punchy",
        "bg": (30, 27, 75),
        "accent": (250, 204, 21),
        "text": (255, 255, 255),
        "muted": (196, 181, 253),
        "pause_ms": 250,
        "max_scenes": 15,
        "target_chars": 150,
    },
}

FORMAT_SIZES = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


@dataclass
class StoryScene:
    index: int
    text: str
    caption: str


@dataclass
class StoryVideoResult:
    path: Path
    filename: str
    scenes_count: int
    duration_seconds: float
    preset: str
    format: str


class StoryVideoService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.out_dir = Path(settings.output_folder) / "stories"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.voice = VoiceService(settings)

    def list_presets(self) -> List[dict]:
        return [
            {"id": k, "label": v["label"], "description": v["description"]}
            for k, v in PRESETS.items()
        ]

    def generate(
        self,
        *,
        story: str,
        preset: str = "narracion",
        instructions: str = "",
        format: str = "9:16",
        voice_id: str = "es-MX-DaliaNeural",
        mood: str = "neutral",
        language: str = "es",
        on_progress: Optional[ProgressCb] = None,
        should_cancel: Optional[CancelCb] = None,
    ) -> StoryVideoResult:
        cleaned = (story or "").strip()
        if len(cleaned) < 20:
            raise InvalidFileError("La historia debe tener al menos 20 caracteres")
        if len(cleaned) > 20000:
            raise InvalidFileError("Máximo 20000 caracteres")

        def check_cancel() -> None:
            if should_cancel and should_cancel():
                raise JobCancelledError()

        preset_key = preset if preset in PRESETS else "narracion"
        fmt = format if format in FORMAT_SIZES else "9:16"
        width, height = FORMAT_SIZES[fmt]
        style = dict(PRESETS[preset_key])
        style = self._apply_instructions(style, instructions or "")

        def prog(pct: int, detail: str, eta: Optional[int] = None) -> None:
            check_cancel()
            if on_progress:
                on_progress(pct, detail, eta)

        check_cancel()
        prog(3, "Partiendo historia en escenas…")
        scenes = self.split_scenes(
            cleaned,
            max_scenes=int(style["max_scenes"]),
            target_chars=int(style["target_chars"]),
        )
        if not scenes:
            raise InvalidFileError("No se pudieron crear escenas a partir del texto")

        work = self.out_dir / f"_work_{uuid.uuid4().hex}"
        work.mkdir(parents=True, exist_ok=True)
        clip_paths: List[Path] = []

        try:
            n = len(scenes)
            for i, scene in enumerate(scenes):
                check_cancel()
                base = 8 + int(80 * i / max(n, 1))
                prog(
                    base,
                    f"Escena {i + 1}/{n}: narración…",
                    eta=max(5, (n - i) * 8),
                )
                audio = self.voice.synthesize(
                    text=scene.text,
                    voice_id=voice_id,
                    mood=mood,
                )
                check_cancel()
                audio_path = work / f"a_{i:03d}.mp3"
                shutil.move(str(audio.path), str(audio_path))
                duration = self._probe_duration(audio_path)
                if duration < 0.4:
                    duration = max(0.8, len(scene.text) / 14.0)

                prog(
                    base + 2,
                    f"Escena {i + 1}/{n}: visual…",
                    eta=max(4, (n - i) * 7),
                )
                img_path = work / f"v_{i:03d}.png"
                self._render_scene_image(
                    img_path,
                    scene=scene,
                    width=width,
                    height=height,
                    style=style,
                    instructions=instructions or "",
                    language=language,
                    scene_total=n,
                )

                check_cancel()
                clip = work / f"c_{i:03d}.mp4"
                self._image_audio_to_clip(
                    img_path,
                    audio_path,
                    clip,
                    duration=duration,
                    width=width,
                    height=height,
                    pause_ms=int(style["pause_ms"]),
                )
                clip_paths.append(clip)

            check_cancel()
            prog(90, "Uniendo escenas…", 6)
            out_name = f"story_{uuid.uuid4().hex}.mp4"
            out_path = self.out_dir / out_name
            self._concat_clips(clip_paths, out_path)

            total_dur = self._probe_duration(out_path)
            if not out_path.exists() or out_path.stat().st_size < 1024:
                raise AppError("El render no produjo un video válido")

            check_cancel()
            prog(100, "Video listo", None)
            logger.info(
                "Story video %s scenes=%d dur=%.1fs → %s",
                preset_key,
                n,
                total_dur,
                out_name,
            )
            return StoryVideoResult(
                path=out_path.resolve(),
                filename=out_name,
                scenes_count=n,
                duration_seconds=round(total_dur, 2),
                preset=preset_key,
                format=fmt,
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def split_scenes(
        self,
        text: str,
        *,
        max_scenes: int = 12,
        target_chars: int = 220,
    ) -> List[StoryScene]:
        max_scenes = max(4, min(15, max_scenes))
        target_chars = max(80, min(400, target_chars))

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        raw_units: List[str] = []
        if len(paragraphs) >= 2:
            for p in paragraphs:
                raw_units.extend(self._split_sentences(p))
        else:
            raw_units = self._split_sentences(text)

        if not raw_units:
            raw_units = [text.strip()]

        # Preferir 1 escena por oración si caben y no son enormes
        if 2 <= len(raw_units) <= max_scenes and all(
            len(u) <= int(target_chars * 1.35) for u in raw_units
        ):
            chunks = list(raw_units)
        else:
            # Agrupar hasta target_chars
            chunks = []
            buf = ""
            for unit in raw_units:
                candidate = f"{buf} {unit}".strip() if buf else unit
                if buf and len(candidate) > target_chars:
                    chunks.append(buf)
                    buf = unit
                else:
                    buf = candidate
            if buf:
                chunks.append(buf)

        # Si hay demasiados, fusionar
        while len(chunks) > max_scenes:
            merged: List[str] = []
            i = 0
            while i < len(chunks):
                if i + 1 < len(chunks) and len(merged) + (len(chunks) - i) // 2 >= max_scenes:
                    merged.append(f"{chunks[i]} {chunks[i + 1]}".strip())
                    i += 2
                else:
                    merged.append(chunks[i])
                    i += 1
            chunks = merged
            if len(chunks) > max_scenes:
                # fuerza: juntar de a dos desde el final
                last = chunks.pop()
                chunks[-1] = f"{chunks[-1]} {last}".strip()

        # Si muy pocos y texto largo, partir por tamaño
        if len(chunks) < 4 and len(text) > target_chars * 3:
            chunks = self._force_chunk(text, target_chars, max_scenes)

        scenes: List[StoryScene] = []
        for i, chunk in enumerate(chunks[:max_scenes]):
            caption = self._caption_from(chunk)
            scenes.append(StoryScene(index=i, text=chunk.strip(), caption=caption))
        return scenes

    def resolve_file(self, filename: str) -> Path:
        safe = Path(filename).name
        if not re.match(r"^story_[a-f0-9]+\.mp4$", safe):
            raise AppError("Archivo de historia inválido", status_code=400)
        path = (self.out_dir / safe).resolve()
        if not str(path).startswith(str(self.out_dir.resolve())):
            raise AppError("Ruta no permitida", status_code=400)
        if not path.exists():
            raise AppError("Video no encontrado", status_code=404)
        return path

    # —— helpers ——

    def _apply_instructions(self, style: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        low = instructions.lower()
        out = dict(style)
        if any(w in low for w in ("rápido", "rapido", "fast", "ágil", "agil", "tiktok")):
            out["pause_ms"] = max(150, int(out["pause_ms"] * 0.65))
            out["target_chars"] = max(100, int(out["target_chars"] * 0.75))
            out["max_scenes"] = min(15, int(out["max_scenes"]) + 2)
        if any(w in low for w in ("lento", "pausado", "slow", "calma")):
            out["pause_ms"] = min(900, int(out["pause_ms"] * 1.4))
            out["target_chars"] = min(320, int(out["target_chars"] * 1.2))
        if any(w in low for w in ("oscuro", "dark", "noche", "gótico", "gotico")):
            out["bg"] = tuple(max(0, c - 8) for c in out["bg"])
            out["muted"] = tuple(max(0, c - 20) for c in out["muted"])
        if any(w in low for w in ("claro", "bright", "día", "dia")):
            out["bg"] = tuple(min(255, c + 40) for c in out["bg"])
            out["text"] = (20, 20, 24)
            out["muted"] = (80, 80, 90)
        if "frases cortas" in low or "punchy" in low:
            out["target_chars"] = max(90, int(out["target_chars"] * 0.6))
            out["max_scenes"] = min(15, int(out["max_scenes"]) + 3)
        return out

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?…])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _force_chunk(self, text: str, target: int, max_scenes: int) -> List[str]:
        words = text.split()
        chunks: List[str] = []
        buf: List[str] = []
        count = 0
        for w in words:
            buf.append(w)
            count += len(w) + 1
            if count >= target and len(chunks) < max_scenes - 1:
                chunks.append(" ".join(buf))
                buf = []
                count = 0
        if buf:
            chunks.append(" ".join(buf))
        return chunks or [text]

    def _caption_from(self, text: str) -> str:
        t = re.sub(r"\s+", " ", text).strip()
        if len(t) <= 72:
            return t
        cut = t[:72]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        return cut + "…"

    def _render_scene_image(
        self,
        path: Path,
        *,
        scene: StoryScene,
        width: int,
        height: int,
        style: Dict[str, Any],
        instructions: str,
        language: str,
        scene_total: int,
    ) -> None:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise AppError(
                "Pillow no está instalado. Ejecuta: pip install Pillow",
                status_code=500,
            ) from exc

        bg = style["bg"]
        accent = style["accent"]
        text_c = style["text"]
        muted = style["muted"]

        img = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)

        # Gradiente / bandas decorativas
        for y in range(height):
            factor = y / max(height - 1, 1)
            r = int(bg[0] * (1 - factor * 0.35) + accent[0] * factor * 0.12)
            g = int(bg[1] * (1 - factor * 0.35) + accent[1] * factor * 0.12)
            b = int(bg[2] * (1 - factor * 0.35) + accent[2] * factor * 0.12)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Forma de acento
        margin = int(width * 0.08)
        bar_h = max(6, height // 180)
        draw.rounded_rectangle(
            [margin, int(height * 0.12), width - margin, int(height * 0.12) + bar_h],
            radius=bar_h // 2,
            fill=accent,
        )

        title_font = self._load_font(size=max(36, width // 18))
        body_font = self._load_font(size=max(28, width // 28))
        small_font = self._load_font(size=max(22, width // 40))

        label = f"Escena {scene.index + 1} / {scene_total}"
        draw.text((margin, int(height * 0.14)), label, fill=muted, font=small_font)

        # Caption grande
        caption_lines = self._wrap_text(draw, scene.caption, title_font, width - 2 * margin)
        y = int(height * 0.22)
        for line in caption_lines[:4]:
            draw.text((margin, y), line, fill=text_c, font=title_font)
            y += title_font.size + 12

        # Cuerpo (texto de escena, más líneas)
        body_lines = self._wrap_text(draw, scene.text, body_font, width - 2 * margin)
        y = int(height * 0.48)
        max_body = 10 if height > width else 6
        for line in body_lines[:max_body]:
            draw.text((margin, y), line, fill=text_c, font=body_font)
            y += body_font.size + 10

        # Instrucciones / tipo (footer hint)
        hint = (instructions or "").strip()
        if hint:
            hint = hint if len(hint) <= 80 else hint[:77] + "…"
            draw.text(
                (margin, height - int(height * 0.08)),
                hint,
                fill=muted,
                font=small_font,
            )
        else:
            lang_label = "ES" if language.startswith("es") else language.upper()
            draw.text(
                (margin, height - int(height * 0.08)),
                f"ClipAI · Historias · {lang_label}",
                fill=muted,
                font=small_font,
            )

        # Círculo decorativo
        r = int(min(width, height) * 0.12)
        cx, cy = width - margin - r, int(height * 0.18)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=max(3, width // 400))

        img.save(path, format="PNG", optimize=True)

    def _load_font(self, size: int):
        from PIL import ImageFont

        candidates = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
        for path in candidates:
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size=size)
                except OSError:
                    continue
        return ImageFont.load_default()

    def _wrap_text(self, draw, text: str, font, max_width: int) -> List[str]:
        words = text.split()
        if not words:
            return []
        lines: List[str] = []
        cur = words[0]
        for w in words[1:]:
            trial = f"{cur} {w}"
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def _probe_duration(self, path: Path) -> float:
        ffprobe = self._ffprobe()
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return float((result.stdout or "0").strip() or 0)
        except Exception:  # noqa: BLE001
            return 0.0

    def _ffmpeg(self) -> str:
        ffmpeg = self.settings.ffmpeg_path
        if shutil.which(ffmpeg) or Path(ffmpeg).exists():
            return ffmpeg
        raise AppError("FFmpeg no encontrado", status_code=500)

    def _ffprobe(self) -> str:
        ffmpeg = Path(self.settings.ffmpeg_path)
        name = ffmpeg.name.replace("ffmpeg", "ffprobe").replace("FFmpeg", "ffprobe")
        candidate = str(ffmpeg.with_name(name)) if ffmpeg.parent != Path(".") else name
        return shutil.which(candidate) or shutil.which("ffprobe") or "ffprobe"

    def _image_audio_to_clip(
        self,
        image: Path,
        audio: Path,
        output: Path,
        *,
        duration: float,
        width: int,
        height: int,
        pause_ms: int,
    ) -> None:
        ffmpeg = self._ffmpeg()
        # Añadir silencio al final del audio vía apad en el clip
        pad = max(0.05, pause_ms / 1000.0)
        total = duration + pad
        frames = max(25, int(total * 25))
        # Ken Burns suave
        vf = (
            f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
            f"crop={width * 2}:{height * 2},"
            f"zoompan=z='min(1.0+0.0008*on\\,{1.08})':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={width}x{height}:fps=25,"
            f"format=yuv420p"
        )
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(image),
                "-i",
                str(audio),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-t",
                f"{total:.3f}",
                "-movflags",
                "+faststart",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.exists():
            # Fallback sin zoompan
            result2 = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(image),
                    "-i",
                    str(audio),
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    "-t",
                    f"{total:.3f}",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result2.returncode != 0 or not output.exists():
                err = (result2.stderr or result.stderr or "")[-400:]
                raise AppError(f"No se pudo renderizar escena: {err}")

    def _concat_clips(self, clips: Sequence[Path], output: Path) -> None:
        ffmpeg = self._ffmpeg()
        list_file = clips[0].parent / "concat.txt"
        lines = []
        for p in clips:
            safe = str(p.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
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
                "-movflags",
                "+faststart",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.exists():
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
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result2.returncode != 0 or not output.exists():
                err = (result2.stderr or result.stderr or "")[-400:]
                raise AppError(f"No se pudo unir el video: {err}")
