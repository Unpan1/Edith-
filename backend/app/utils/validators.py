"""Validación de archivos de video."""

from pathlib import Path

from app.config.settings import Settings
from app.utils.exceptions import FileTooLargeError, InvalidFileError


def validate_video_extension(filename: str, settings: Settings) -> str:
    """Valida la extensión del archivo y retorna la extensión en minúsculas."""
    if not filename or "." not in filename:
        raise InvalidFileError("El archivo no tiene extensión válida")

    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions_list:
        allowed = ", ".join(settings.allowed_extensions_list)
        raise InvalidFileError(f"Extensión '{ext}' no permitida. Permitidas: {allowed}")
    return ext


def validate_file_size(size_bytes: int, settings: Settings) -> None:
    """Valida que el tamaño no exceda el límite configurado."""
    if size_bytes <= 0:
        raise InvalidFileError("El archivo está vacío")
    if size_bytes > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"El archivo ({size_bytes / (1024 * 1024):.1f} MB) excede el límite "
            f"de {settings.max_upload_size_mb} MB"
        )


def format_duration(seconds: float) -> str:
    """Formatea segundos a MM:SS o HH:MM:SS."""
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Formatea bytes a representación legible."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
