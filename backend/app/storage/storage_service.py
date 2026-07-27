"""Servicio de almacenamiento local con nombres UUID."""

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

from app.config.settings import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Gestiona subida, lectura y eliminación de archivos en disco."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.upload_dir = Path(settings.upload_folder)
        self.output_dir = Path(settings.output_folder)
        self.temp_dir = Path(settings.temp_folder)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in (self.upload_dir, self.output_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)

    def generate_uuid_name(self, extension: str) -> str:
        """Genera un nombre único basado en UUID (evita sobrescrituras)."""
        ext = extension if extension.startswith(".") else f".{extension}"
        return f"{uuid.uuid4().hex}{ext.lower()}"

    def save_upload(self, file_obj: BinaryIO, original_filename: str, extension: str) -> Path:
        """Guarda un archivo subido con nombre UUID. Retorna la ruta absoluta."""
        filename = self.generate_uuid_name(extension)
        dest = self.upload_dir / filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(file_obj, out)
        logger.info("Archivo guardado: %s (original: %s)", dest, original_filename)
        return dest.resolve()

    def get_output_path(self, name: Optional[str] = None, extension: str = ".mp4") -> Path:
        filename = name or self.generate_uuid_name(extension)
        return (self.output_dir / filename).resolve()

    def get_temp_path(self, extension: str = ".wav") -> Path:
        return (self.temp_dir / self.generate_uuid_name(extension)).resolve()

    def clip_dir(self, video_id: int) -> Path:
        path = self.output_dir / f"video_{video_id}"
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def delete_path(self, path: str | Path) -> None:
        p = Path(path)
        try:
            if p.is_file():
                p.unlink(missing_ok=True)
                logger.info("Archivo eliminado: %s", p)
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                logger.info("Directorio eliminado: %s", p)
        except OSError as exc:
            logger.warning("No se pudo eliminar %s: %s", p, exc)

    def delete_video_assets(self, video_ruta: str, video_id: int) -> None:
        """Elimina el video original y todos los outputs asociados."""
        self.delete_path(video_ruta)
        self.delete_path(self.output_dir / f"video_{video_id}")
