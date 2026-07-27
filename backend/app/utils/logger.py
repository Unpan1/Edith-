"""Configuración de logging estructurado."""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """Inicializa el logger raíz de la aplicación."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Silenciar ruido de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "clipai")
