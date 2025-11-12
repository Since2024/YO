"""Database configuration and session management using SQLAlchemy."""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


def _build_database_url() -> str:
    """Build SQLAlchemy database URL from environment variables."""
    driver = os.getenv("DB_DRIVER")
    if not driver:
        # Default to SQLite when no explicit configuration is provided.
        if any(os.getenv(key) for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")):
            driver = "mysql"
        else:
            driver = "sqlite"
    driver = driver.lower()

    if driver == "sqlite":
        db_path = Path(os.getenv("DB_PATH", "data/autoformfill.db")).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    name = os.getenv("DB_NAME", "autoformfill")

    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        "?charset=utf8mb4"
    )


DATABASE_URL = _build_database_url()
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"

engine = create_engine(
    DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


@contextmanager
def get_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database session rolled back due to error")
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create database tables if they do not exist."""
    from .models import Base  # pylint: disable=import-outside-toplevel

    logger.info("Ensuring database tables exist")
    Base.metadata.create_all(bind=engine)


def get_engine():
    """Expose the SQLAlchemy engine."""
    return engine
