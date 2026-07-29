"""Editor de video básico local (FFmpeg): pegar, recortar, espejo, volúmenes."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from app.config.settings import Settings
from app.utils.exceptions import AppError, InvalidFileError, JobCancelledError
from app.utils.logger import get_logger

logger = get_logger(__name__)

ProgressCb = Callable[[int, str, Optional[int]], None]
CancelCb = Callable[[], bool]

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


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
                if stream.get("codec_type") == "video":
                    width = stream.get("width")
                    height = stream.get("height")
                    break
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
        else:
            raise InvalidFileError("Sube un video (mp4/mov/…) o audio (mp3/wav/…)")

        asset_id = uuid.uuid4().hex
        safe_ext = ext if ext else (".mp4" if kind == "video" else ".mp3")
        dest = self.assets_dir / f"{asset_id}{safe_ext}"
        dest.write_bytes(data)
        info = self.probe(dest)
        asset = EditAsset(
            id=asset_id,
            kind=kind,
            path=dest.resolve(),
            original_name=Path(filename).name[:180],
            size_bytes=dest.stat().st_size,
            duration=info.get("duration"),
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

    def list_assets(self) -> List[EditAsset]:
        return [a for a in self._assets.values() if a.path.exists()]

    def resolve_output(self, filename: str) -> Path:
        safe = Path(filename).name
        if not re.match(r"^edit_[a-f0-9]+\.mp4$", safe):
            raise AppError("Archivo inválido", status_code=400)
        path = (self.out_dir / safe).resolve()
        if not str(path).startswith(str(self.out_dir.resolve())):
            raise AppError("Ruta no permitida", status_code=400)
        if not path.exists():
            raise AppError("Video no encontrado", status_code=404)
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

    def _run(self, args: List[str]) -> None:
        cmd = [self._ffmpeg(), "-y", *args]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "")[-500:]
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
