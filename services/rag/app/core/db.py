"""Shared SQLAlchemy engine for the RAG service."""
from __future__ import annotations

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return _engine
