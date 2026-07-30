"""Editor de video con timeline local (FFmpeg): pistas, fotos, audio, títulos."""

from __future__ import annotations

import json
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

ProgressCb = Callable[[int, str, Optional[int]], None]
CancelCb = Callable[[], bool]

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

FONT_MAP = {
    "Arial": "arial.ttf",
    "Arial Black": "ariblk.ttf",
    "Times New Roman": "times.ttf",
    "Courier New": "cour.ttf",
    "Verdana": "verdana.ttf",
    "Comic Sans MS": "comic.ttf",
    "Impact": "impact.ttf",
    "Georgia": "georgia.ttf",
    "Trebuchet MS": "trebuc.ttf",
    "Segoe UI": "segoeui.ttf",
}


@dataclass
class EditAsset:
    id: str
    kind: str
    path: Path
    original_name: str
    size_bytes: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class EditResult:
    path: Path
    filename: str
    duration: float
    size_bytes: int


class BasicEditService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = Path(settings.output_folder) / "basic_edit"
        self.assets_dir = self.root / "assets"
        self.out_dir = self.root / "out"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.root / "assets_index.json"
        self._assets: Dict[str, EditAsset] = {}
        self._load_index()

    def _ffmpeg(self) -> str:
        ff = self.settings.ffmpeg_path
        if shutil.which(ff) or Path(ff).exists():
            return ff
        raise AppError("FFmpeg no encontrado", status_code=500)

    def _ffprobe(self) -> str:
        ffmpeg = Path(self.settings.ffmpeg_path)
        name = ffmpeg.name.replace("ffmpeg", "ffprobe").replace("FFmpeg", "ffprobe")
        candidate = str(ffmpeg.with_name(name)) if ffmpeg.parent != Path(".") else name
        return shutil.which(candidate) or shutil.which("ffprobe") or "ffprobe"

    def _load_index(self) -> None:
        if not self._meta_path.exists():
            return
        try:
            data = json.loads(self._meta_path.read_text(encoding="utf-8"))
            for item in data:
                path = Path(item["path"])
                if not path.exists():
                    continue
                self._assets[item["id"]] = EditAsset(
                    id=item["id"],
                    kind=item["kind"],
                    path=path,
                    original_name=item.get("original_name") or path.name,
                    size_bytes=int(item.get("size_bytes") or path.stat().st_size),
                    duration=item.get("duration"),
                    width=item.get("width"),
                    height=item.get("height"),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo cargar índice de assets: %s", exc)

    def _save_index(self) -> None:
        payload = [
            {
                "id": a.id,
                "kind": a.kind,
                "path": str(a.path),
                "original_name": a.original_name,
                "size_bytes": a.size_bytes,
                "duration": a.duration,
                "width": a.width,
                "height": a.height,
            }
            for a in self._assets.values()
        ]
        self._meta_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def probe(self, path: Path) -> dict:
        try:
            result = subprocess.run(
                [
                    self._ffprobe(),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration:stream=width,height,codec_type",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(result.stdout or "{}")
            duration = float((data.get("format") or {}).get("duration") or 0) or None
            width = height = None
            for stream in data.get("streams") or []:
                if stream.get("codec_type") in ("video", None) or stream.get("width"):
                    width = stream.get("width") or width
                    height = stream.get("height") or height
                    if stream.get("codec_type") == "video":
                        break
            # imágenes a veces solo reportan streams sin duration útil
            if path.suffix.lower() in IMAGE_EXTS:
                duration = None
            return {"duration": duration, "width": width, "height": height}
        except Exception:  # noqa: BLE001
            return {"duration": None, "width": None, "height": None}

    def save_upload(self, *, filename: str, data: bytes, kind_hint: str = "auto") -> EditAsset:
        if not data:
            raise InvalidFileError("Archivo vacío")
        if len(data) > self.settings.max_upload_size_bytes:
            raise AppError(
                f"El archivo supera {self.settings.max_upload_size_mb} MB",
                status_code=413,
            )
        ext = Path(filename).suffix.lower()
        if kind_hint == "video" or (kind_hint == "auto" and ext in VIDEO_EXTS):
            if ext not in VIDEO_EXTS:
                raise InvalidFileError("Formato de video no soportado")
            kind = "video"
        elif kind_hint == "audio" or (kind_hint == "auto" and ext in AUDIO_EXTS):
            if ext not in AUDIO_EXTS:
                raise InvalidFileError("Formato de audio no soportado")
            kind = "audio"
        elif kind_hint == "image" or (kind_hint == "auto" and ext in IMAGE_EXTS):
            if ext not in IMAGE_EXTS:
                raise InvalidFileError("Formato de imagen no soportado")
            kind = "image"
        else:
            raise InvalidFileError(
                "Sube video (mp4/mov/…), imagen (jpg/png/…) o audio (mp3/wav/…)"
            )

        asset_id = uuid.uuid4().hex
        if kind == "video":
            safe_ext = ext if ext else ".mp4"
        elif kind == "audio":
            safe_ext = ext if ext else ".mp3"
        else:
            safe_ext = ext if ext else ".jpg"
        dest = self.assets_dir / f"{asset_id}{safe_ext}"
        dest.write_bytes(data)
        info = self.probe(dest)
        duration = info.get("duration")
        if kind == "image":
            duration = None  # la duración la define el usuario en la timeline
        asset = EditAsset(
            id=asset_id,
            kind=kind,
            path=dest.resolve(),
            original_name=Path(filename).name[:180],
            size_bytes=dest.stat().st_size,
            duration=duration,
            width=info.get("width"),
            height=info.get("height"),
        )
        self._assets[asset_id] = asset
        self._save_index()
        return asset

    def get_asset(self, asset_id: str) -> EditAsset:
        asset = self._assets.get(asset_id)
        if not asset or not asset.path.exists():
            raise AppError("Archivo no encontrado", status_code=404)
        return asset

    def resolve_font(self, family: str) -> Optional[Path]:
        name = FONT_MAP.get(family) or FONT_MAP.get("Arial")
        candidates = [
            Path(r"C:\Windows\Fonts") / name,
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ]
        for c in candidates:
            if c.exists():
                return c
        # búsqueda genérica en Windows Fonts
        win = Path(r"C:\Windows\Fonts")
        if win.exists() and name:
            for p in win.glob(name.replace(".ttf", ".*")):
                return p
        return None

    def render_timeline(
        self,
        *,
        clips: Sequence[Any],
        width: int = 1280,
        height: int = 720,
        mirror: bool = False,
        export_format: str = "mp4",
        on_progress: Optional[ProgressCb] = None,
        should_cancel: Optional[CancelCb] = None,
    ) -> EditResult:
        def check() -> None:
            if should_cancel and should_cancel():
                raise JobCancelledError()

        def prog(pct: int, detail: str, eta: Optional[int] = None) -> None:
            check()
            if on_progress:
                on_progress(pct, detail, eta)

        width = max(320, int(width) - int(width) % 2)
        height = max(240, int(height) - int(height) % 2)

        visual: List[Any] = []
        titles: List[Any] = []
        audios: List[Any] = []
        for c in clips:
            kind = getattr(c, "kind", None) or c.get("kind")
            if kind in ("video", "image"):
                visual.append(c)
            elif kind == "title":
                titles.append(c)
            elif kind == "audio":
                audios.append(c)

        if not visual and not titles and not audios:
            raise InvalidFileError(
                "Añade al menos un video, foto, título o audio en la timeline"
            )

        total = 0.0
        for c in list(clips):
            start = float(getattr(c, "start", 0) if not isinstance(c, dict) else c["start"])
            dur = float(
                getattr(c, "duration", 0) if not isinstance(c, dict) else c["duration"]
            )
            total = max(total, start + dur)
        total = max(0.5, total)

        work = self.root / f"_tl_{uuid.uuid4().hex}"
        work.mkdir(parents=True, exist_ok=True)

        try:
            prog(5, "Creando lienzo…")
            canvas = work / "canvas.mp4"
            self._make_canvas(canvas, width, height, total)

            current = canvas
            sorted_visual = sorted(
                visual,
                key=lambda c: float(
                    getattr(c, "start", 0) if not isinstance(c, dict) else c["start"]
                ),
            )
            n_vis = max(1, len(sorted_visual))
            for i, clip in enumerate(sorted_visual):
                check()
                pct = 10 + int(50 * (i / n_vis))
                prog(pct, f"Colocando clip {i + 1}/{len(sorted_visual)}…")
                start = float(
                    getattr(clip, "start", 0) if not isinstance(clip, dict) else clip["start"]
                )
                duration = float(
                    getattr(clip, "duration", 1)
                    if not isinstance(clip, dict)
                    else clip["duration"]
                )
                asset_id = (
                    getattr(clip, "asset_id", None)
                    if not isinstance(clip, dict)
                    else clip.get("asset_id")
                )
                kind = getattr(clip, "kind", None) if not isinstance(clip, dict) else clip["kind"]
                if not asset_id:
                    raise InvalidFileError("Clip visual sin asset")
                asset = self.get_asset(asset_id)
                if kind == "image" and asset.kind != "image":
                    raise InvalidFileError(f"{asset.original_name} no es una imagen")
                if kind == "video" and asset.kind != "video":
                    raise InvalidFileError(f"{asset.original_name} no es un video")

                seg = work / f"seg_{i:03d}.mp4"
                source_offset = float(self._clip_get(clip, "source_offset", 0) or 0)
                self._materialize_visual(
                    asset,
                    seg,
                    duration=duration,
                    width=width,
                    height=height,
                    source_offset=source_offset,
                )
                overlaid = work / f"ov_{i:03d}.mp4"
                self._overlay_at(current, seg, overlaid, start=start, duration=duration)
                current = overlaid

            check()
            prog(65, "Aplicando títulos…")
            titled = work / "titled.mp4"
            if titles:
                self._burn_titles(current, titled, titles, mirror=mirror)
                current = titled
            elif mirror:
                self._run(
                    [
                        "-i",
                        str(current),
                        "-vf",
                        "hflip",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-an",
                        "-movflags",
                        "+faststart",
                        str(titled),
                    ]
                )
                current = titled

            check()
            prog(78, "Mezclando audio…")
            master = work / "master.mp4"
            self._mix_timeline_audio(
                current,
                master,
                visual_clips=sorted_visual,
                audio_clips=audios,
                total=total,
            )

            check()
            fmt = (export_format or "mp4").lower().strip()
            allowed = {"mp4", "webm", "mov", "mkv", "gif", "mp3", "wav"}
            if fmt not in allowed:
                raise InvalidFileError(f"Formato no soportado: {fmt}")

            prog(90, f"Exportando a {fmt.upper()}…")
            out_name = f"edit_{uuid.uuid4().hex}.{fmt}"
            out_path = self.out_dir / out_name
            self._transcode_export(master, out_path, fmt)

            check()
            prog(95, "Validando salida…")
            min_size = 256 if fmt in ("mp3", "wav", "gif") else 1024
            if not out_path.exists() or out_path.stat().st_size < min_size:
                raise AppError("El render no produjo un archivo válido")
            final_info = self.probe(out_path)
            duration = float(final_info.get("duration") or total)
            size = out_path.stat().st_size
            prog(100, "Listo", None)
            logger.info(
                "Timeline edit → %s (%.1fs, %.1f MB) clips=%d fmt=%s",
                out_name,
                duration,
                size / 1024 / 1024,
                len(list(clips)),
                fmt,
            )
            return EditResult(
                path=out_path.resolve(),
                filename=out_name,
                duration=round(duration, 2),
                size_bytes=size,
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _transcode_export(self, src: Path, dst: Path, fmt: str) -> None:
        """Convierte el master MP4 al formato de exportación elegido."""
        if fmt == "mp4":
            # Ya es mp4 usable; copiar rápido
            shutil.copy2(src, dst)
            return

        if fmt == "mov":
            self._run(
                [
                    "-i",
                    str(src),
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
                    "-movflags",
                    "+faststart",
                    str(dst),
                ]
            )
            return

        if fmt == "mkv":
            self._run(
                [
                    "-i",
                    str(src),
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
                    str(dst),
                ]
            )
            return

        if fmt == "webm":
            self._run(
                [
                    "-i",
                    str(src),
                    "-c:v",
                    "libvpx-vp9",
                    "-b:v",
                    "1.5M",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "128k",
                    str(dst),
                ]
            )
            return

        if fmt == "gif":
            # GIF sin audio, paleta para mejor calidad
            palette = dst.with_suffix(".png")
            try:
                self._run(
                    [
                        "-i",
                        str(src),
                        "-vf",
                        "fps=12,scale=480:-1:flags=lanczos,palettegen",
                        str(palette),
                    ]
                )
                self._run(
                    [
                        "-i",
                        str(src),
                        "-i",
                        str(palette),
                        "-lavfi",
                        "fps=12,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse",
                        "-loop",
                        "0",
                        str(dst),
                    ]
                )
            finally:
                if palette.exists():
                    palette.unlink(missing_ok=True)
            return

        if fmt == "mp3":
            self._run(
                [
                    "-i",
                    str(src),
                    "-vn",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    str(dst),
                ]
            )
            return

        if fmt == "wav":
            self._run(
                [
                    "-i",
                    str(src),
                    "-vn",
                    "-c:a",
                    "pcm_s16le",
                    str(dst),
                ]
            )
            return

        raise InvalidFileError(f"Formato no soportado: {fmt}")

    def _clip_get(self, clip: Any, key: str, default: Any = None) -> Any:
        if isinstance(clip, dict):
            return clip.get(key, default)
        return getattr(clip, key, default)

    def _make_canvas(self, dst: Path, width: int, height: int, duration: float) -> None:
        self._run(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={width}x{height}:d={duration:.3f}:r=30",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(dst),
            ]
        )

    def _materialize_visual(
        self,
        asset: EditAsset,
        dst: Path,
        *,
        duration: float,
        width: int,
        height: int,
        source_offset: float = 0.0,
    ) -> None:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
        )
        source_offset = max(0.0, float(source_offset or 0))
        if asset.kind == "image":
            self._run(
                [
                    "-loop",
                    "1",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    str(asset.path),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-tune",
                    "stillimage",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-an",
                    "-movflags",
                    "+faststart",
                    str(dst),
                ]
            )
            return
        # video: desde source_offset durante duration
        try:
            self._run(
                [
                    "-ss",
                    f"{source_offset:.3f}",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    str(asset.path),
                    "-vf",
                    vf,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-movflags",
                    "+faststart",
                    str(dst),
                ]
            )
        except AppError:
            self._run(
                [
                    "-ss",
                    f"{source_offset:.3f}",
                    "-i",
                    str(asset.path),
                    "-vf",
                    f"{vf},tpad=stop_mode=clone:stop_duration={duration:.3f}",
                    "-t",
                    f"{duration:.3f}",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-movflags",
                    "+faststart",
                    str(dst),
                ]
            )

    def _overlay_at(
        self,
        base: Path,
        clip: Path,
        dst: Path,
        *,
        start: float,
        duration: float,
    ) -> None:
        end = start + duration
        fc = (
            f"[1:v]setpts=PTS-STARTPTS+{start:.3f}/TB[ov];"
            f"[0:v][ov]overlay=eof_action=pass:enable='between(t\\,{start:.3f}\\,{end:.3f})'[v]"
        )
        self._run(
            [
                "-i",
                str(base),
                "-i",
                str(clip),
                "-filter_complex",
                fc,
                "-map",
                "[v]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                str(dst),
            ]
        )

    def _escape_drawtext(self, text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
            .replace("\n", " ")
        )[:200]

    def _burn_titles(
        self,
        src: Path,
        dst: Path,
        titles: Sequence[Any],
        *,
        mirror: bool,
    ) -> None:
        """Quema títulos con drawtext. Usa textfile + fuente local (evita bugs de Windows)."""
        work = dst.parent
        parts: List[str] = []
        if mirror:
            parts.append("hflip")

        for i, t in enumerate(titles):
            raw = str(self._clip_get(t, "text") or "Titulo")[:200]
            text_path = work / f"title_{i}.txt"
            text_path.write_text(raw, encoding="utf-8")

            size = int(self._clip_get(t, "font_size", 48) or 48)
            color = str(self._clip_get(t, "color", "white") or "white")
            if not re.match(r"^[A-Za-z]+$|^0x[0-9A-Fa-f]{6,8}$|^#[0-9A-Fa-f]{6,8}$", color):
                color = "white"
            family = str(self._clip_get(t, "font_family", "Arial") or "Arial")
            start = float(self._clip_get(t, "start", 0) or 0)
            duration = float(self._clip_get(t, "duration", 3) or 3)
            end = start + duration
            x_pct = float(self._clip_get(t, "x_percent", 50) or 50)
            y_pct = float(self._clip_get(t, "y_percent", 18) or 18)
            x_expr = f"(w*{x_pct / 100:.4f})-(text_w/2)"
            y_expr = f"(h*{y_pct / 100:.4f})-(text_h/2)"

            font_name = None
            font = self.resolve_font(family) or self.resolve_font("Arial")
            if font and font.exists():
                font_name = f"title_font_{i}{font.suffix.lower() or '.ttf'}"
                local = work / font_name
                if not local.exists():
                    shutil.copy2(font, local)

            opts = [
                f"textfile=title_{i}.txt",
                "reload=0",
                f"fontsize={size}",
                f"fontcolor={color}",
                "borderw=3",
                "bordercolor=black@0.7",
                f"x={x_expr}",
                f"y={y_expr}",
                f"enable=between(t\\,{start:.3f}\\,{end:.3f})",
            ]
            if font_name:
                opts.insert(1, f"fontfile={font_name}")
            parts.append("drawtext=" + ":".join(opts))

        vf = ",".join(parts) if parts else "null"
        try:
            self._run(
                [
                    "-i",
                    str(src.resolve()),
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
                    "160k",
                    "-movflags",
                    "+faststart",
                    str(dst.resolve()),
                ],
                cwd=work,
            )
        except AppError:
            # Fallback sin fuente personalizada
            parts_fb: List[str] = []
            if mirror:
                parts_fb.append("hflip")
            for i, t in enumerate(titles):
                raw = self._escape_drawtext(str(self._clip_get(t, "text") or "Titulo"))
                size = int(self._clip_get(t, "font_size", 48) or 48)
                start = float(self._clip_get(t, "start", 0) or 0)
                duration = float(self._clip_get(t, "duration", 3) or 3)
                end = start + duration
                x_pct = float(self._clip_get(t, "x_percent", 50) or 50)
                y_pct = float(self._clip_get(t, "y_percent", 18) or 18)
                parts_fb.append(
                    f"drawtext=text='{raw}':fontsize={size}:fontcolor=white:"
                    f"borderw=3:bordercolor=black@0.7:"
                    f"x=(w*{x_pct / 100:.4f})-(text_w/2):"
                    f"y=(h*{y_pct / 100:.4f})-(text_h/2):"
                    f"enable=between(t\\,{start:.3f}\\,{end:.3f})"
                )
            self._run(
                [
                    "-i",
                    str(src.resolve()),
                    "-vf",
                    ",".join(parts_fb),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-movflags",
                    "+faststart",
                    str(dst.resolve()),
                ],
                cwd=work,
            )

    def _mix_timeline_audio(
        self,
        video: Path,
        dst: Path,
        *,
        visual_clips: Sequence[Any],
        audio_clips: Sequence[Any],
        total: float,
    ) -> None:
        """Mezcla audio de videos + pistas de audio externas con volumen y offset."""
        inputs: List[str] = ["-i", str(video)]
        filters: List[str] = []
        labels: List[str] = []
        idx = 1

        # Audio original de cada video en su posición (si volume > 0)
        for clip in visual_clips:
            if self._clip_get(clip, "kind") != "video":
                continue
            vol = float(self._clip_get(clip, "volume", 1.0) or 0)
            if vol <= 0.001:
                continue
            asset_id = self._clip_get(clip, "asset_id")
            if not asset_id:
                continue
            asset = self.get_asset(asset_id)
            start = float(self._clip_get(clip, "start", 0) or 0)
            duration = float(self._clip_get(clip, "duration", 1) or 1)
            src_off = float(self._clip_get(clip, "source_offset", 0) or 0)
            delay_ms = int(start * 1000)
            inputs += ["-i", str(asset.path)]
            lab = f"va{idx}"
            filters.append(
                f"[{idx}:a]atrim={src_off:.3f}:{src_off + duration:.3f},asetpts=PTS-STARTPTS,"
                f"volume={vol:.3f},adelay={delay_ms}|{delay_ms},apad=whole_dur={total:.3f}[{lab}]"
            )
            labels.append(f"[{lab}]")
            idx += 1

        for clip in audio_clips:
            asset_id = self._clip_get(clip, "asset_id")
            if not asset_id:
                continue
            asset = self.get_asset(asset_id)
            if asset.kind != "audio":
                continue
            vol = float(self._clip_get(clip, "volume", 1.0) or 1.0)
            start = float(self._clip_get(clip, "start", 0) or 0)
            duration = float(self._clip_get(clip, "duration", 1) or 1)
            src_off = float(self._clip_get(clip, "source_offset", 0) or 0)
            delay_ms = int(start * 1000)
            inputs += ["-i", str(asset.path)]
            lab = f"aa{idx}"
            filters.append(
                f"[{idx}:a]atrim={src_off:.3f}:{src_off + duration:.3f},asetpts=PTS-STARTPTS,"
                f"volume={vol:.3f},adelay={delay_ms}|{delay_ms},apad=whole_dur={total:.3f}[{lab}]"
            )
            labels.append(f"[{lab}]")
            idx += 1

        if not labels:
            # sin audio extra: copiar video (puede no tener audio)
            try:
                self._run(
                    [
                        *inputs,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-t",
                        f"{total:.3f}",
                        "-movflags",
                        "+faststart",
                        str(dst),
                    ]
                )
            except AppError:
                self._run(
                    [
                        "-i",
                        str(video),
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=44100:cl=stereo",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-shortest",
                        "-t",
                        f"{total:.3f}",
                        "-movflags",
                        "+faststart",
                        str(dst),
                    ]
                )
            return

        n = len(labels)
        mix = "".join(labels) + f"amix=inputs={n}:duration=longest:dropout_transition=0[aout]"
        fc = ";".join(filters + [mix])
        self._run(
            [
                *inputs,
                "-filter_complex",
                fc,
                "-map",
                "0:v",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                f"{total:.3f}",
                "-movflags",
                "+faststart",
                str(dst),
            ]
        )
        asset = self._assets.get(asset_id)
        if not asset or not asset.path.exists():
            raise AppError("Archivo no encontrado", status_code=404)
        return asset

    def list_assets(self) -> List[EditAsset]:
        return [a for a in self._assets.values() if a.path.exists()]

    def resolve_output(self, filename: str) -> Path:
        safe = Path(filename).name
        if not re.match(
            r"^edit_[a-f0-9]+\.(mp4|webm|mov|mkv|gif|mp3|wav)$", safe, re.I
        ):
            raise AppError("Archivo inválido", status_code=400)
        path = (self.out_dir / safe).resolve()
        if not str(path).startswith(str(self.out_dir.resolve())):
            raise AppError("Ruta no permitida", status_code=400)
        if not path.exists():
            raise AppError("Archivo no encontrado", status_code=404)
        return path

    def render(
        self,
        *,
        video_ids: Sequence[str],
        audio_id: Optional[str] = None,
        start: float = 0.0,
        end: Optional[float] = None,
        mirror: bool = False,
        video_volume: float = 1.0,
        audio_volume: float = 1.0,
        audio_mode: str = "mix",
        on_progress: Optional[ProgressCb] = None,
        should_cancel: Optional[CancelCb] = None,
    ) -> EditResult:
        def check() -> None:
            if should_cancel and should_cancel():
                raise JobCancelledError()

        def prog(pct: int, detail: str, eta: Optional[int] = None) -> None:
            check()
            if on_progress:
                on_progress(pct, detail, eta)

        videos = [self.get_asset(vid) for vid in video_ids]
        for v in videos:
            if v.kind != "video":
                raise InvalidFileError(f"{v.original_name} no es un video")

        audio: Optional[EditAsset] = None
        if audio_id and audio_mode != "keep":
            audio = self.get_asset(audio_id)
            if audio.kind != "audio":
                raise InvalidFileError("El archivo de audio no es válido")

        video_volume = max(0.0, min(2.0, float(video_volume)))
        audio_volume = max(0.0, min(2.0, float(audio_volume)))
        start = max(0.0, float(start))
        if end is not None and end <= start:
            raise InvalidFileError("El fin del recorte debe ser mayor que el inicio")

        work = self.root / f"_work_{uuid.uuid4().hex}"
        work.mkdir(parents=True, exist_ok=True)

        try:
            prog(5, "Preparando clips…")
            check()

            # 1) Concatenar videos si hay varios
            if len(videos) == 1:
                base = videos[0].path
                prog(20, "Video base listo")
            else:
                prog(10, f"Pegando {len(videos)} videos…")
                base = work / "concat.mp4"
                self._concat_videos([v.path for v in videos], base)
                prog(35, "Videos unidos")

            check()
            # 2) Recorte
            trimmed = work / "trimmed.mp4"
            info = self.probe(base)
            total = float(info.get("duration") or 0) or None
            trim_end = end
            if trim_end is None and total:
                trim_end = total
            if start > 0.05 or (trim_end is not None and total and trim_end < total - 0.05):
                prog(40, "Recortando…")
                self._trim(base, trimmed, start, trim_end)
                current = trimmed
            else:
                current = base
                prog(45, "Sin recorte")

            check()
            # 3) Espejo + volumen + audio externo
            prog(55, "Aplicando efectos…")
            out_name = f"edit_{uuid.uuid4().hex}.mp4"
            out_path = self.out_dir / out_name
            self._apply_fx(
                current,
                out_path,
                mirror=mirror,
                video_volume=video_volume,
                audio_path=audio.path if audio else None,
                audio_volume=audio_volume,
                audio_mode=audio_mode if audio else "keep",
            )

            check()
            prog(95, "Validando salida…")
            if not out_path.exists() or out_path.stat().st_size < 1024:
                raise AppError("El render no produjo un video válido")
            final_info = self.probe(out_path)
            duration = float(final_info.get("duration") or 0)
            size = out_path.stat().st_size
            prog(100, "Listo", None)
            logger.info(
                "Basic edit → %s (%.1fs, %.1f MB) mirror=%s",
                out_name,
                duration,
                size / 1024 / 1024,
                mirror,
            )
            return EditResult(
                path=out_path.resolve(),
                filename=out_name,
                duration=round(duration, 2),
                size_bytes=size,
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _run(self, args: List[str], cwd: Optional[Path] = None) -> None:
        cmd = [self._ffmpeg(), "-y", *args]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd) if cwd else None,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "")[-800:]
            raise AppError(f"FFmpeg falló: {err}")

    def _trim(self, src: Path, dst: Path, start: float, end: Optional[float]) -> None:
        duration = None if end is None else max(0.1, end - start)
        args = ["-ss", f"{start:.3f}", "-i", str(src)]
        if duration is not None:
            args += ["-t", f"{duration:.3f}"]
        args += [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(dst),
        ]
        self._run(args)

    def _concat_videos(self, parts: Sequence[Path], output: Path) -> None:
        """Re-encode concat para unificar codecs/resolución."""
        first = self.probe(parts[0])
        w = int(first.get("width") or 1280)
        h = int(first.get("height") or 720)
        w -= w % 2
        h -= h % 2
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
        )

        norm_dir = output.parent / "norm"
        norm_dir.mkdir(exist_ok=True)
        normalized: List[Path] = []
        for i, p in enumerate(parts):
            np = norm_dir / f"n_{i:03d}.mp4"
            try:
                self._run(
                    [
                        "-i",
                        str(p),
                        "-vf",
                        vf,
                        "-af",
                        "aformat=sample_rates=44100:channel_layouts=stereo",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-c:a",
                        "aac",
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        "-movflags",
                        "+faststart",
                        str(np),
                    ]
                )
            except AppError:
                self._run(
                    [
                        "-i",
                        str(p),
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=44100:cl=stereo",
                        "-vf",
                        vf,
                        "-map",
                        "0:v",
                        "-map",
                        "1:a",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-c:a",
                        "aac",
                        "-shortest",
                        "-movflags",
                        "+faststart",
                        str(np),
                    ]
                )
            normalized.append(np)

        list_file = output.parent / "concat.txt"
        lines = []
        for p in normalized:
            safe = str(p.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
        list_file.write_text("\n".join(lines), encoding="utf-8")
        self._run(
            [
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
            ]
        )

    def _apply_fx(
        self,
        src: Path,
        dst: Path,
        *,
        mirror: bool,
        video_volume: float,
        audio_path: Optional[Path],
        audio_volume: float,
        audio_mode: str,
    ) -> None:
        vf_parts = []
        if mirror:
            vf_parts.append("hflip")
        vf = ",".join(vf_parts) if vf_parts else None

        # Sin audio externo
        if not audio_path or audio_mode == "keep":
            args = ["-i", str(src)]
            if vf:
                args += ["-vf", vf]
            args += [
                "-af",
                f"volume={video_volume:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                str(dst),
            ]
            try:
                self._run(args)
                return
            except AppError:
                # Video sin pista de audio
                args = ["-i", str(src)]
                if vf:
                    args += ["-vf", vf]
                args += [
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-movflags",
                    "+faststart",
                    str(dst),
                ]
                self._run(args)
                return

        # Con audio externo
        args = ["-i", str(src), "-i", str(audio_path)]
        if audio_mode == "replace":
            fc = f"[1:a]volume={audio_volume:.3f}[a]"
            maps_v = "0:v"
            if vf:
                args += ["-vf", vf]
            args += [
                "-filter_complex",
                fc,
                "-map",
                maps_v,
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(dst),
            ]
            self._run(args)
            return

        # mix
        fc = (
            f"[0:a]volume={video_volume:.3f}[a0];"
            f"[1:a]volume={audio_volume:.3f}[a1];"
            f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
        if vf:
            args += ["-vf", vf]
        args += [
            "-filter_complex",
            fc,
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(dst),
        ]
        try:
            self._run(args)
        except AppError:
            # Si el video no tiene audio, solo usar el externo
            args = ["-i", str(src), "-i", str(audio_path)]
            if vf:
                args += ["-vf", vf]
            args += [
                "-filter_complex",
                f"[1:a]volume={audio_volume:.3f}[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(dst),
            ]
            self._run(args)
