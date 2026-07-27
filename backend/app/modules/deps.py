"""Dependencias compartidas de módulos SaaS."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db

DEFAULT_USER_ID = 1


def get_current_user_id() -> int:
    """Usuario bootstrap por defecto (sin auth real aún)."""
    return DEFAULT_USER_ID


@lru_cache
def get_job_queue():
    from app.modules.jobs.queue import InMemoryJobQueue, get_shared_queue

    return get_shared_queue()
