"""Sesión SQLAlchemy y dependencia de inyección para FastAPI."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Yield de sesión DB por request (cierre automático)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
