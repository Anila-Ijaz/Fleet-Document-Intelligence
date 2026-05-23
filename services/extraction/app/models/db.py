"""Database models and session management (SQLAlchemy 2.0 style).

One table for documents and their extracted fields. The pgvector embedding column is
added in Phase 2 for the RAG service; we leave a clean migration path.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    document_type: Mapped[str] = mapped_column(String(64), index=True)
    raw_text: Mapped[str] = mapped_column(Text)

    # The full validated extraction, stored as JSON for flexibility + queryability.
    extracted: Mapped[dict] = mapped_column(JSON)

    confidence: Mapped[float] = mapped_column(Float)
    needs_review: Mapped[bool] = mapped_column(default=False, index=True)

    # A few denormalised columns for fast filtering/analytics without JSON queries.
    supplier_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    gross_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


_engine = None
_SessionLocal = None


def init_engine() -> None:
    global _engine, _SessionLocal
    if _engine is None:
        s = get_settings()
        _engine = create_engine(s.database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def create_tables() -> None:
    init_engine()
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    init_engine()
    return _SessionLocal()
