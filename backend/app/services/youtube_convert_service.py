"""Convierte videos de YouTube a MP4 y/o MP3 (yt-dlp + FFmpeg, gratis)."""

from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from app.config.settings import Settings
from app.utils.exceptions import AppError, InvalidFileError, JobCancelledError
from app.utils.logger import get_logger
from app.video.youtube_service import YoutubeService

logger = get_logger(__name__)

ProgressCb = Callable[[int, str, Optional[int]], None]
CancelCb = Callable[[], bool]


@dataclass
class ConvertedFile:
    kind: str  # mp4 | mp3
    path: Path
    filename: str
    size_bytes: int
    display_name: str = ""


@dataclass
class YoutubeConvertResult:
    title: str
    duration: Optional[float]
    format: str
    files: List[ConvertedFile] = field(default_factory=list)


class YoutubeConvertService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.out_dir = Path(settings.output_folder) / "youtube_convert"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.youtube = YoutubeService(settings)

    def convert(
        self,
        url: str,
        *,
        fmt: str = "both",
        on_progress: Optional[ProgressCb] = None,
        should_cancel: Optional[CancelCb] = None,
    ) -> YoutubeConvertResult:
        fmt = (fmt or "both").lower().strip()
        if fmt not in ("mp4", "mp3", "both"):
            raise InvalidFileError("Formato inválido. Usa mp4, mp3 o both")

        def check() -> None:
            if should_cancel and should_cancel():
                raise JobCancelledError()

        def prog(pct: int, detail: str, eta: Optional[int] = None) -> None:
            check()
            if on_progress:
                on_progress(pct, detail, eta)

        clean = self.youtube.normalize_url(url)
        work = self.out_dir / f"_work_{uuid.uuid4().hex}"
        work.mkdir(parents=True, exist_ok=True)
        files: List[ConvertedFile] = []

        try:
            check()
            if fmt in ("mp4", "both"):
                prog(5, "Descargando video (MP4)…")

                def mp4_progress(pct: int, detail: str, eta: Optional[int]) -> None:
                    # Mapear 0–100 de yt-dlp a 5–70
                    mapped = 5 + int(pct * 0.65)
                    prog(mapped, detail, eta)

                dl = self.youtube.download(
                    clean, work, on_progress=mp4_progress
                )
                check()
                token = uuid.uuid4().hex
                safe = self._safe_stem(dl.title)
                mp4_name = f"yt_{token}.mp4"
                mp4_path = self.out_dir / mp4_name
                shutil.move(str(dl.path), str(mp4_path))
                files.append(
                    ConvertedFile(
                        kind="mp4",
                        path=mp4_path.resolve(),
                        filename=mp4_name,
                        size_bytes=mp4_path.stat().st_size,
                        display_name=f"{safe}.mp4",
                    )
                )
                title = safe
                duration = dl.duration

                if fmt == "both":
                    prog(75, "Extrayendo audio MP3…", 10)
                    check()
                    mp3_name = f"yt_{token}.mp3"
                    mp3_path = self.out_dir / mp3_name
                    self._extract_mp3(mp4_path, mp3_path)
                    files.append(
                        ConvertedFile(
                            kind="mp3",
                            path=mp3_path.resolve(),
                            filename=mp3_name,
                            size_bytes=mp3_path.stat().st_size,
                            display_name=f"{safe}.mp3",
                        )
                    )
            else:
                # Solo MP3
                prog(5, "Descargando audio…")

                def audio_progress(pct: int, detail: str, eta: Optional[int]) -> None:
                    mapped = 5 + int(pct * 0.8)
                    prog(mapped, detail, eta)

                audio = self._download_audio_mp3(
                    clean, work, on_progress=audio_progress
                )
                check()
                token = uuid.uuid4().hex
                safe = self._safe_stem(audio["title"])
                mp3_name = f"yt_{token}.mp3"
                mp3_path = self.out_dir / mp3_name
                shutil.move(str(audio["path"]), str(mp3_path))
                files.append(
                    ConvertedFile(
                        kind="mp3",
                        path=mp3_path.resolve(),
                        filename=mp3_name,
                        size_bytes=mp3_path.stat().st_size,
                        display_name=f"{safe}.mp3",
                    )
                )
                title = safe
                duration = audio.get("duration")

            check()
            prog(100, "Conversión lista", None)
            logger.info(
                "YouTube convert %s → %s (%d archivos)",
                fmt,
                title,
                len(files),
            )
            return YoutubeConvertResult(
                title=title,
                duration=duration,
                format=fmt,
                files=files,
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def resolve_file(self, filename: str) -> Path:
        from urllib.parse import unquote

        safe = Path(unquote(filename or "")).name
        if not re.match(r"^yt_[a-f0-9]+", safe, re.I):
            raise AppError("Archivo inválido", status_code=400)
        if Path(safe).suffix.lower() not in (".mp4", ".mp3"):
            raise AppError("Archivo inválido", status_code=400)

        root = self.out_dir.resolve()
        path = (self.out_dir / safe).resolve()
        if path.exists() and str(path).startswith(str(root)):
            return path

        # Legacy: archivos con título/emoji en el nombre
        m = re.match(r"^(yt_[a-f0-9]+)", safe, re.I)
        ext = Path(safe).suffix.lower()
        if m:
            for cand in sorted(self.out_dir.glob(f"{m.group(1)}*{ext}")):
                resolved = cand.resolve()
                if str(resolved).startswith(str(root)) and resolved.exists():
                    return resolved
        raise AppError("Archivo no encontrado", status_code=404)

    def _safe_stem(self, title: str) -> str:
        base = re.sub(r"\.mp4$", "", title or "", flags=re.I)
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
        base = re.sub(r"_+", "_", base).strip("._") or "youtube"
        return base[:80]

    def _ffmpeg(self) -> str:
        ffmpeg = self.settings.ffmpeg_path
        if shutil.which(ffmpeg) or Path(ffmpeg).exists():
            return ffmpeg
        raise AppError("FFmpeg no encontrado", status_code=500)

    def _extract_mp3(self, video: Path, output: Path) -> None:
        ffmpeg = self._ffmpeg()
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-q:a",
                "2",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not output.exists() or output.stat().st_size < 64:
            err = (result.stderr or "")[-300:]
            raise AppError(f"No se pudo extraer MP3: {err}")

    def _download_audio_mp3(
        self,
        url: str,
        dest_dir: Path,
        on_progress: Optional[ProgressCb] = None,
    ) -> dict:
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise AppError(
                "yt-dlp no está instalado. Ejecuta: pip install yt-dlp",
                status_code=500,
            ) from exc

        import time

        outtmpl = str(dest_dir / "%(id)s.%(ext)s")
        last = {"t": 0.0}

        def _hook(d: dict) -> None:
            if not on_progress:
                return
            now = time.time()
            if d.get("status") == "downloading" and now - last["t"] < 0.35:
                return
            last["t"] = now
            if d.get("status") == "downloading":
                downloaded = float(d.get("downloaded_bytes") or 0)
                total = float(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                eta = d.get("eta")
                eta_i = int(eta) if isinstance(eta, (int, float)) else None
                if total > 0:
                    pct = int((downloaded / total) * 100)
                    detail = f"Audio {downloaded / 1e6:.1f}/{total / 1e6:.1f} MB"
                else:
                    pct = min(90, int(downloaded / 1e6) + 5)
                    detail = f"Descargando audio… ({downloaded / 1e6:.1f} MB)"
                on_progress(pct, detail, eta_i)
            elif d.get("status") == "finished":
                on_progress(95, "Convirtiendo a MP3…", 5)

        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "progress_hooks": [_hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        ffmpeg_parent = Path(self.settings.ffmpeg_path).parent
        if ffmpeg_parent.exists():
            ydl_opts["ffmpeg_location"] = str(ffmpeg_parent)

        if on_progress:
            on_progress(2, "Obteniendo información…", None)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise AppError("No se pudo obtener información del video")
            if "entries" in info and info["entries"]:
                info = info["entries"][0]
            vid = info.get("id")
            candidates = list(dest_dir.glob(f"{vid}*.mp3")) if vid else []
            if not candidates:
                candidates = list(dest_dir.glob("*.mp3"))
            if not candidates:
                raise AppError("La descarga de audio no generó un MP3")
            path = candidates[0]
            title = (info.get("title") or path.stem or "youtube").strip()
            duration = info.get("duration")
            try:
                duration_f = float(duration) if duration is not None else None
            except (TypeError, ValueError):
                duration_f = None

        return {"path": path.resolve(), "title": title, "duration": duration_f}
