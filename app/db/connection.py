"""Minimal SQLAlchemy connection handling."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import data_dir
from app.utils import get_logger

logger = get_logger(__name__)


def _build_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    mysql_host = os.getenv("MYSQL_HOST")
    if mysql_host or os.getenv("DB_HOST"):
        host = mysql_host or os.getenv("DB_HOST", "localhost")
        user = os.getenv("MYSQL_USER") or os.getenv("DB_USER", "root")
        password = os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD", "")
        name = os.getenv("MYSQL_DB") or os.getenv("DB_NAME", "firstchild")
        port = os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", "3306")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"

    sqlite_path = Path(os.getenv("SQLITE_PATH", data_dir() / "mvp.sqlite3"))
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path}"


DATABASE_URL = _build_url()
ENGINE = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Iterator:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("DB transaction rolled back")
        raise
    finally:
        session.close()


def init_db() -> None:
    from .models import Base

    Base.metadata.create_all(ENGINE)
    logger.info("Database ready (%s)", DATABASE_URL.split("://", 1)[0])


__all__ = ["get_session", "init_db", "ENGINE"]

