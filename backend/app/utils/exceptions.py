"""Excepciones de dominio de la aplicación."""

from typing import Optional


class AppError(Exception):
    """Error base de la aplicación."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidFileError(AppError):
    def __init__(self, message: str = "Archivo inválido"):
        super().__init__(message, status_code=400)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "El archivo excede el tamaño máximo permitido"):
        super().__init__(message, status_code=413)


class VideoNotFoundError(AppError):
    def __init__(self, video_id: int):
        super().__init__(f"Video {video_id} no encontrado", status_code=404)


class ClipNotFoundError(AppError):
    def __init__(self, clip_id: int):
        super().__init__(f"Clip {clip_id} no encontrado", status_code=404)


class CorruptVideoError(AppError):
    def __init__(self, message: str = "El video parece estar corrupto o no es legible"):
        super().__init__(message, status_code=422)


class FFmpegNotFoundError(AppError):
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message or "FFmpeg no está instalado o no se encuentra en el PATH",
            status_code=500,
        )


class WhisperNotAvailableError(AppError):
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message or "Whisper no está disponible. Verifica la instalación del modelo.",
            status_code=500,
        )


class ProcessingError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class JobCancelledError(AppError):
    def __init__(self, message: str = "Generación cancelada"):
        super().__init__(message, status_code=499)


class DatabaseError(AppError):
    def __init__(self, message: str = "Error de base de datos MySQL"):
        super().__init__(message, status_code=500)
