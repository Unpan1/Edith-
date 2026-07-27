"""Servicio FFmpeg: extracción de audio, clips, subtítulos incrustados, miniaturas."""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from app.config.settings import Settings
from app.utils.exceptions import CorruptVideoError, FFmpegNotFoundError, ProcessingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FFmpegService:
    """Wrapper profesional sobre FFmpeg / FFprobe."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.ffmpeg = settings.ffmpeg_path
        self.ffprobe = self._resolve_ffprobe()
        self._verified = False

    def _resolve_ffprobe(self) -> str:
        ffmpeg_path = Path(self.ffmpeg)
        if ffmpeg_path.name.lower().startswith("ffmpeg"):
            candidate = ffmpeg_path.with_name(
                ffmpeg_path.name.replace("ffmpeg", "ffprobe").replace("FFmpeg", "ffprobe")
            )
            if candidate.exists() or shutil.which(str(candidate)):
                return str(candidate)
        return shutil.which("ffprobe") or "ffprobe"

    def _verify_ffmpeg(self) -> None:
        if self._verified:
            return
        if not shutil.which(self.ffmpeg) and not Path(self.ffmpeg).exists():
            raise FFmpegNotFoundError(
                f"FFmpeg no encontrado en '{self.ffmpeg}'. Instálalo o configura FFMPEG_PATH."
            )
        self._verified = True

    def _run(
        self,
        args: list[str],
        *,
        timeout: Optional[int] = 600,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self._verify_ffmpeg()
        cmd = [self.ffmpeg, "-y", *args]
        logger.debug("FFmpeg: %s", " ".join(cmd))
        start = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError() from exc
        except subprocess.TimeoutExpired as exc:
            raise ProcessingError("FFmpeg excedió el tiempo límite") from exc

        elapsed = time.perf_counter() - start
        logger.info("FFmpeg finalizó en %.2fs (code=%s)", elapsed, result.returncode)

        if check and result.returncode != 0:
            stderr = (result.stderr or "")[-2000:]
            logger.error("FFmpeg error: %s", stderr)
            raise ProcessingError(f"Error de FFmpeg: {stderr[-500:]}")
        return result

    def get_video_info(self, video_path: str | Path) -> Tuple[float, int, int]:
        """
        Retorna (duración_segundos, ancho, alto).
        Lanza CorruptVideoError si el archivo no es legible.
        """
        self._verify_ffmpeg()
        path = Path(video_path)
        if not path.exists():
            raise CorruptVideoError(f"Archivo no encontrado: {path}")

        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError("FFprobe no encontrado") from exc

        if result.returncode != 0:
            raise CorruptVideoError("No se pudo leer el video (posible corrupción)")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CorruptVideoError("Metadatos de video ilegibles") from exc

        duration = float(data.get("format", {}).get("duration") or 0)
        width = height = 0
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width") or 0)
                height = int(stream.get("height") or 0)
                break

        if duration <= 0:
            raise CorruptVideoError("Duración del video inválida o cero")

        return duration, width, height

    def extract_audio(self, video_path: str | Path, output_wav: str | Path) -> Path:
        """Extrae audio a WAV mono 16 kHz (óptimo para Whisper)."""
        out = Path(output_wav)
        out.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Extrayendo audio: %s → %s", video_path, out)
        self._run([
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(out),
        ])
        if not out.exists() or out.stat().st_size == 0:
            raise ProcessingError("La extracción de audio produjo un archivo vacío")
        return out

    def cut_clip(
        self,
        video_path: str | Path,
        output_path: str | Path,
        start: float,
        end: float,
    ) -> Path:
        """Corta un segmento del video (re-encode para precisión de cortes)."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.1, end - start)
        logger.info("Generando clip [%.2f–%.2f] → %s", start, end, out)
        self._run([
            "-ss", f"{start:.3f}",
            "-i", str(video_path),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(out),
        ])
        return out

    def burn_subtitles(
        self,
        video_path: str | Path,
        subtitle_path: str | Path,
        output_path: str | Path,
        style_name: str = "clean",
        *,
        use_ass: bool = False,
    ) -> Path:
        """Incrusta subtítulos ASS (recomendado) o SRT en el video."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        sub = Path(subtitle_path).resolve()
        escaped = str(sub).replace("\\", "/").replace(":", "\\:")

        if use_ass or sub.suffix.lower() == ".ass":
            # ASS ya trae estilos propios (sin caja opaca, karaoke, etc.)
            vf = f"ass='{escaped}'"
        else:
            # Fallback SRT limpio (outline, SIN BorderStyle=3)
            styles = {
                "clean": (
                    "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
                    "Bold=1,Alignment=2,MarginV=80"
                ),
                "social": (
                    "FontName=Arial Black,FontSize=22,PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,"
                    "Bold=1,Alignment=2,MarginV=90"
                ),
                "subtle": (
                    "FontName=Arial,FontSize=14,PrimaryColour=&H00F0F0F0,"
                    "OutlineColour=&H00000000,BorderStyle=1,Outline=1.5,Shadow=0,"
                    "Alignment=2,MarginV=60"
                ),
                "boxed": (
                    "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,"
                    "Outline=0,Shadow=0,Alignment=2,MarginV=80"
                ),
            }
            style = styles.get(style_name, styles["clean"])
            vf = f"subtitles='{escaped}':force_style='{style}'"

        logger.info("Incrustando subtítulos (%s, ass=%s): %s", style_name, use_ass, sub.name)
        self._run([
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(out),
        ])
        return out

    @staticmethod
    def _mirror_suffix(mirror: bool) -> str:
        return ",hflip" if mirror else ""

    def cut_and_reformat(
        self,
        video_path: str | Path,
        output_path: str | Path,
        *,
        start: float,
        end: float,
        out_w: int,
        out_h: int,
        fill_mode: str = "smart_crop",
        focus_box: Optional[Tuple[int, int, int, int]] = None,
        src_size: Optional[Tuple[int, int]] = None,
        mirror_horizontal: bool = False,
    ) -> Path:
        """Corta y adapta a resolución objetivo (crop / blur / letterbox)."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.1, end - start)
        use_complex = fill_mode == "blur_bg"
        vf = self._build_reformat_filter(
            out_w, out_h, fill_mode, focus_box, src_size, mirror_horizontal
        )
        logger.info(
            "Reformat [%s] %dx%d [%.2f–%.2f] crop=%s → %s",
            fill_mode, out_w, out_h, start, end, focus_box, out,
        )
        if use_complex:
            self._run([
                "-ss", f"{start:.3f}",
                "-i", str(video_path),
                "-t", f"{duration:.3f}",
                "-filter_complex", vf,
                "-map", "[vout]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "160k",
                "-movflags", "+faststart",
                str(out),
            ])
        else:
            self._run([
                "-ss", f"{start:.3f}",
                "-i", str(video_path),
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "160k",
                "-movflags", "+faststart",
                str(out),
            ])
        return out

    def cut_interview_stack(
        self,
        video_path: str | Path,
        output_path: str | Path,
        *,
        start: float,
        end: float,
        out_w: int,
        half_h: int,
        top_box: Tuple[int, int, int, int],
        bottom_box: Tuple[int, int, int, int],
        mirror_horizontal: bool = False,
    ) -> Path:
        """Apila dos recortes de hablantes (arriba / abajo) en formato vertical."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.1, end - start)
        tx, ty, tw, th = top_box
        bx, by, bw, bh = bottom_box
        # Asegurar dims pares para x264
        out_w -= out_w % 2
        half_h -= half_h % 2

        mirror = self._mirror_suffix(mirror_horizontal)
        fc = (
            f"[0:v]split=2[v0][v1];"
            f"[v0]crop={tw}:{th}:{tx}:{ty},scale={out_w}:{half_h}:flags=lanczos,"
            f"setsar=1[top];"
            f"[v1]crop={bw}:{bh}:{bx}:{by},scale={out_w}:{half_h}:flags=lanczos,"
            f"setsar=1[bot];"
            f"[top][bot]vstack=inputs=2{mirror}[vout]"
        )
        logger.info("Interview stack [%.2f–%.2f] top=%s bot=%s → %s", start, end, top_box, bottom_box, out)
        self._run([
            "-ss", f"{start:.3f}",
            "-i", str(video_path),
            "-t", f"{duration:.3f}",
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            str(out),
        ])
        return out

    def concat_clips(self, parts: list[Path], output_path: str | Path) -> Path:
        """Concatena clips (mismo codec) vía concat demuxer."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        list_file = out.parent / f"{out.stem}_concat.txt"
        lines = []
        for p in parts:
            # Escapar comillas simples en path para concat
            safe = str(p.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
        list_file.write_text("\n".join(lines), encoding="utf-8")
        try:
            self._run([
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(out),
            ])
        finally:
            list_file.unlink(missing_ok=True)
        return out

    @staticmethod
    def _build_reformat_filter(
        out_w: int,
        out_h: int,
        fill_mode: str,
        focus_box: Optional[Tuple[int, int, int, int]],
        src_size: Optional[Tuple[int, int]] = None,
        mirror_horizontal: bool = False,
    ) -> str:
        mirror = FFmpegService._mirror_suffix(mirror_horizontal)
        out_w -= out_w % 2
        out_h -= out_h % 2

        if fill_mode == "letterbox":
            return (
                f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1{mirror}"
            )

        if fill_mode == "blur_bg":
            # Sujeto encaja completo (sin zoom destructivo) + fondo difuminado
            return (
                f"[0:v]split[original][bg];"
                f"[bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={out_w}:{out_h},gblur=sigma=20[blurred];"
                f"[original]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
                f"[blurred][fg]overlay=(W-w)/2:(H-h)/2,setsar=1{mirror}[vout]"
            )

        # smart_crop: focus_box ya viene con el AR correcto y tamaño máximo (alejado)
        if focus_box:
            x, y, w, h = focus_box
            w = max(2, w - w % 2)
            h = max(2, h - h % 2)
            return (
                f"crop={w}:{h}:{x}:{y},"
                f"scale={out_w}:{out_h}:flags=lanczos,"
                f"setsar=1{mirror}"
            )

        # Sin foco: cover central (máximo alejamiento posible)
        return (
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out_w}:{out_h},setsar=1{mirror}"
        )

    def extract_thumbnail(
        self,
        video_path: str | Path,
        output_path: str | Path,
        at_seconds: float = 1.0,
    ) -> Path:
        """Extrae un frame como miniatura JPEG."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            "-ss", f"{max(0, at_seconds):.3f}",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(out),
        ], timeout=60)
        return out

    def burn_thumbnail_text(
        self,
        image_path: str | Path,
        output_path: str | Path,
        text: str,
        *,
        font_size: int = 36,
    ) -> Path:
        """Nuevo: superpone texto simple sobre una miniatura JPEG/PNG."""
        src = Path(image_path)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        safe = (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
        )[:80]
        # drawtext centrado abajo; fallback sin fuente del sistema
        vf = (
            f"drawtext=text='{safe}':fontsize={font_size}:fontcolor=white:"
            f"borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-text_h-40"
        )
        self._run(
            ["-i", str(src), "-vf", vf, "-q:v", "2", str(out)],
            timeout=60,
        )
        return out
