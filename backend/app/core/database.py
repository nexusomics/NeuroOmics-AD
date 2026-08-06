"""Database engine & session management.

Production uses PostgreSQL; development falls back to SQLite automatically when
the configured Postgres is unreachable, so the platform runs anywhere.
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _engine_for(url: str, fallback: bool = False):
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(
            url,
            connect_args=connect_args,
            poolclass=StaticPool if ":memory:" in url else None,
        )
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def _postgres_url() -> str:
    return (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def build_engine():
    """Build engine; gracefully fall back to SQLite if Postgres is unavailable."""
    url = settings.DATABASE_URL
    if url.startswith("postgres"):
        url = _postgres_url()
    try:
        engine = _engine_for(url)
        with engine.connect():
            pass
        logger.info("Database connected: %s", engine.url.drivername)
        return engine
    except Exception as exc:  # noqa: BLE001 - any connection error triggers fallback
        if not settings.DATABASE_URL.startswith("sqlite"):
            logger.warning("PostgreSQL unreachable (%s). Falling back to SQLite (dev mode).", exc)
            fallback_url = "sqlite:///./neuroomics.db"
            engine = _engine_for(fallback_url)
            if engine.dialect.name == "sqlite":

                @event.listens_for(engine, "connect")
                def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()

            return engine
        raise


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency yielding a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (dev; production uses Alembic migrations)."""
    from app import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
