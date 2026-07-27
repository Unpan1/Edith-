"""Descarga videos de YouTube con yt-dlp (gratis, local, sin API de pago)."""

from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from app.config.settings import Settings
from app.utils.exceptions import AppError, InvalidFileError
from app.utils.logger import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str, Optional[int]], None]

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "music.youtube.com",
}


@dataclass
class YoutubeDownloadResult:
    path: Path
    title: str
    duration: Optional[float]
    size_bytes: int


def _fmt_bytes(n: float) -> str:
    if n >= 1024 * 1024 * 1024:
        return f"{n / (1024 ** 3):.2f} GB"
    if n >= 1024 * 1024:
        return f"{n / (1024 ** 2):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{int(n)} B"


class YoutubeService:
    """Importa videos públicos de YouTube vía yt-dlp + FFmpeg local."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def normalize_url(url: str) -> str:
        raw = (url or "").strip()
        if not raw:
            raise InvalidFileError("Pega un enlace de YouTube")
        if not re.match(r"^https?://", raw, re.I):
            raw = "https://" + raw

        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host not in _YOUTUBE_HOSTS:
            raise InvalidFileError(
                "Solo se admiten enlaces de YouTube (youtube.com / youtu.be)"
            )

        if "youtu.be" in host:
            video_id = parsed.path.strip("/").split("/")[0]
            if not video_id:
                raise InvalidFileError("Enlace de YouTube inválido")
            return f"https://www.youtube.com/watch?v={video_id}"

        path = parsed.path or ""
        if path.startswith("/shorts/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else ""
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        if path.startswith("/live/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else ""
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"

        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            return f"https://www.youtube.com/watch?v={qs['v'][0]}"

        if path.startswith("/watch"):
            raise InvalidFileError("El enlace de YouTube no incluye el ID del video")

        return raw

    def download(
        self,
        url: str,
        dest_dir: Path,
        on_progress: Optional[ProgressCallback] = None,
    ) -> YoutubeDownloadResult:
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise AppError(
                "yt-dlp no está instalado. Ejecuta: pip install yt-dlp",
                status_code=500,
            ) from exc

        clean_url = self.normalize_url(url)
        dest_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(dest_dir / "%(id)s.%(ext)s")
        max_mb = self.settings.max_upload_size_mb

        last_report = {"t": 0.0}

        def _hook(d: dict) -> None:
            if not on_progress:
                return
            now = time.time()
            # Limitar frecuencia de updates
            if d.get("status") == "downloading" and now - last_report["t"] < 0.35:
                return
            last_report["t"] = now

            status = d.get("status")
            if status == "downloading":
                downloaded = float(d.get("downloaded_bytes") or 0)
                total = float(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                speed = float(d.get("speed") or 0)
                eta = d.get("eta")
                eta_i = int(eta) if isinstance(eta, (int, float)) and eta is not None else None

                if total > 0:
                    # 5–90% para descarga de bytes
                    pct = 5 + int((downloaded / total) * 85)
                    detail = (
                        f"Descargando {_fmt_bytes(downloaded)} / {_fmt_bytes(total)}"
                    )
                else:
                    pct = max(5, min(90, int(downloaded / (5 * 1024 * 1024)) + 5))
                    detail = f"Descargando {_fmt_bytes(downloaded)}…"

                if speed > 0:
                    detail += f" · {_fmt_bytes(speed)}/s"
                if eta_i is None and speed > 0 and total > downloaded:
                    eta_i = int((total - downloaded) / speed)

                on_progress(pct, detail, eta_i)

            elif status == "finished":
                on_progress(92, "Descarga lista. Uniendo pistas (FFmpeg)…", 8)
            elif status == "error":
                on_progress(0, "Error en la descarga", None)

        if on_progress:
            on_progress(2, "Obteniendo información del video…", None)

        ydl_opts = {
            "outtmpl": outtmpl,
            "format": (
                "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/"
                "b[ext=mp4][height<=1080]/"
                "bv*+ba/b"
            ),
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "fragment_retries": 3,
            "max_filesize": max_mb * 1024 * 1024,
            "progress_hooks": [_hook],
        }
        ffmpeg_parent = Path(self.settings.ffmpeg_path).parent
        if ffmpeg_parent.exists() and (
            not shutil.which("ffmpeg") or Path(self.settings.ffmpeg_path).exists()
        ):
            ydl_opts["ffmpeg_location"] = str(ffmpeg_parent)

        logger.info("Descargando YouTube: %s", clean_url)
        info = None
        path: Path
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                if info is None:
                    raise AppError("No se pudo obtener información del video de YouTube")
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                prepared = ydl.prepare_filename(info)
                path = Path(prepared)
                if path.suffix.lower() != ".mp4":
                    alt = path.with_suffix(".mp4")
                    if alt.exists():
                        path = alt
                if not path.exists():
                    vid = info.get("id")
                    candidates = list(dest_dir.glob(f"{vid}.*")) if vid else []
                    if not candidates:
                        raise AppError("La descarga de YouTube no generó un archivo")
                    path = candidates[0]
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            logger.exception("Error yt-dlp: %s", msg)
            if "Private video" in msg or "private" in msg.lower():
                raise AppError("El video de YouTube es privado o no accesible") from exc
            if "unavailable" in msg.lower() or "not available" in msg.lower():
                raise AppError("El video de YouTube no está disponible") from exc
            if "Sign in" in msg or "bot" in msg.lower():
                raise AppError(
                    "YouTube bloqueó la descarga. Prueba otro video o actualiza yt-dlp."
                ) from exc
            raise AppError(f"No se pudo descargar el video: {msg[:300]}") from exc

        if on_progress:
            on_progress(96, "Validando archivo descargado…", 3)

        size = path.stat().st_size
        if size > self.settings.max_upload_size_bytes:
            path.unlink(missing_ok=True)
            raise AppError(
                f"El video supera el límite de {max_mb} MB",
                status_code=413,
            )

        title = (info.get("title") or path.stem or "youtube_video").strip()
        safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title)[:120] or "youtube_video"
        duration = info.get("duration")
        try:
            duration_f = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_f = None

        logger.info(
            "YouTube descargado: %s (%.1f MB) → %s",
            safe_title,
            size / (1024 * 1024),
            path,
        )
        return YoutubeDownloadResult(
            path=path.resolve(),
            title=f"{safe_title}.mp4",
            duration=duration_f,
            size_bytes=size,
        )
