"""Configuración centralizada de la aplicación mediante variables de entorno."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes cargados desde .env / variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "clipai"
    mysql_user: str = "root"
    mysql_password: str = "root"

    # Almacenamiento
    upload_folder: str = "./uploads"
    output_folder: str = "./outputs"
    temp_folder: str = "./temp"

    # IA / Video
    whisper_model: str = "base"
    ffmpeg_path: str = "ffmpeg"

    # Seguridad
    max_upload_size_mb: int = 500
    allowed_extensions: str = ".mp4,.mov,.avi,.mkv,.webm"

    # CORS / Logs
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    # Clips
    clip_min_duration: float = 20.0
    clip_max_duration: float = 60.0
    max_clips_per_video: int = 8

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Crea las carpetas de trabajo si no existen."""
        for folder in (self.upload_folder, self.output_folder, self.temp_folder):
            Path(folder).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración (inyectable vía FastAPI Depends)."""
    settings = Settings()
    settings.ensure_directories()
    return settings
