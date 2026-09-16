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

_INSTAGRAM_HOSTS = {
    "instagram.com",
    "www.instagram.com",
}

_FACEBOOK_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "web.facebook.com",
    "fb.watch",
    "fb.com",
    "www.fb.com",
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


def yt_dlp_base_opts(*, platform: str = "youtube") -> dict:
    """Opciones comunes de yt-dlp. Evita HTTP 403 de YouTube con cliente android."""
    opts: dict = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        },
    }
    if platform == "youtube":
        # El cliente web suele devolver URLs que caen en 403; android/ios son más estables.
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        }
    return opts


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

    @staticmethod
    def normalize_media_url(url: str) -> tuple[str, str]:
        """Normaliza URL de YouTube, Instagram o Facebook. Devuelve (url, plataforma)."""
        raw = (url or "").strip()
        if not raw:
            raise InvalidFileError("Pega un enlace de YouTube, Instagram o Facebook")
        if not re.match(r"^https?://", raw, re.I):
            raw = "https://" + raw

        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host_key = host
        else:
            host_key = host

        if host_key in _YOUTUBE_HOSTS or host in _YOUTUBE_HOSTS:
            return YoutubeService.normalize_url(raw), "youtube"

        if host_key in _INSTAGRAM_HOSTS or host in _INSTAGRAM_HOSTS:
            path = parsed.path or ""
            if not any(
                p in path
                for p in ("/reel/", "/reels/", "/p/", "/tv/")
            ):
                # Aceptar también perfiles con share links genéricos
                if len(path.strip("/")) < 2:
                    raise InvalidFileError(
                        "Enlace de Instagram inválido. Usa un Reel o publicación (/reel/…)."
                    )
            return raw.split("?")[0].rstrip("/"), "instagram"

        if (
            host_key in _FACEBOOK_HOSTS
            or host in _FACEBOOK_HOSTS
            or host.endswith(".facebook.com")
            or host.endswith(".fb.watch")
            or host == "fb.watch"
        ):
            return raw, "facebook"

        raise InvalidFileError(
            "Solo se admiten YouTube, Instagram (Reels) o Facebook (Reels/videos)"
        )

    def download(
        self,
        url: str,
        dest_dir: Path,
        on_progress: Optional[ProgressCallback] = None,
        *,
        skip_normalize: bool = False,
        platform: str = "youtube",
    ) -> YoutubeDownloadResult:
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise AppError(
                "yt-dlp no está instalado. Ejecuta: pip install yt-dlp",
                status_code=500,
            ) from exc

        if skip_normalize:
            clean_url = (url or "").strip()
        else:
            clean_url, platform = self.normalize_media_url(url)

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
            **yt_dlp_base_opts(platform=platform),
            "outtmpl": outtmpl,
            "format": (
                "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/"
                "b[ext=mp4][height<=1080]/"
                "bv*+ba/b"
            ),
            "merge_output_format": "mp4",
            "max_filesize": max_mb * 1024 * 1024,
            "progress_hooks": [_hook],
        }
        ffmpeg_parent = Path(self.settings.ffmpeg_path).parent
        if ffmpeg_parent.exists() and (
            not shutil.which("ffmpeg") or Path(self.settings.ffmpeg_path).exists()
        ):
            ydl_opts["ffmpeg_location"] = str(ffmpeg_parent)

        label = {"youtube": "YouTube", "instagram": "Instagram", "facebook": "Facebook"}.get(
            platform, platform
        )
        logger.info("Descargando %s: %s", label, clean_url)
        info = None
        path: Path
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                if info is None:
                    raise AppError(f"No se pudo obtener información del video de {label}")
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
                        raise AppError(f"La descarga de {label} no generó un archivo")
                    path = candidates[0]
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            logger.exception("Error yt-dlp (%s): %s", label, msg)
            low = msg.lower()
            if "private" in low:
                raise AppError(f"El video de {label} es privado o no accesible") from exc
            if "unavailable" in low or "not available" in low:
                raise AppError(f"El video de {label} no está disponible") from exc
            if "login" in low or "sign in" in low or "cookie" in low:
                raise AppError(
                    f"{label} pidió inicio de sesión. Prueba un Reel/video público "
                    "o actualiza yt-dlp."
                ) from exc
            if "403" in low or "forbidden" in low:
                raise AppError(
                    f"{label} bloqueó la descarga (403). Reinicia el backend; "
                    "si sigue fallando, actualiza yt-dlp: pip install -U yt-dlp"
                ) from exc
            if "bot" in low:
                raise AppError(
                    f"{label} bloqueó la descarga. Prueba otro enlace o actualiza yt-dlp."
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

        title = (info.get("title") or info.get("id") or path.stem or f"{platform}_video").strip()
        safe_title = re.sub(r'[<>:"/\\|?*]+', "_", title)[:120] or f"{platform}_video"
        duration = info.get("duration")
        try:
            duration_f = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_f = None

        logger.info(
            "%s descargado: %s (%.1f MB) → %s",
            label,
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
