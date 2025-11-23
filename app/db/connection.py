"""Minimal SQLAlchemy connection handling."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app import data_dir
from app.utils import get_logger

logger = get_logger(__name__)


def _build_url() -> str:
    """Build database URL - prefers MySQL if configured, falls back to SQLite."""
    
    # Check for explicit DATABASE_URL
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    
    # Check for MySQL configuration
    mysql_host = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST")
    if mysql_host:
        host = mysql_host
        user = os.getenv("MYSQL_USER") or os.getenv("DB_USER", "root")
        password = os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD", "")
        name = os.getenv("MYSQL_DB") or os.getenv("DB_NAME", "fomo")
        port = os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", "3306")
        
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
        logger.info(f"Attempting MySQL database: {name}@{host}")
        return url
    
    # Default to SQLite
    sqlite_path = Path(os.getenv("SQLITE_PATH", data_dir() / "fomo.sqlite3"))
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using SQLite database: {sqlite_path}")
    return f"sqlite:///{sqlite_path}"


def _test_connection(engine) -> bool:
    """Test if database connection works."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connection test failed: {e}")
        return False


def _get_sqlite_url() -> str:
    """Get SQLite database URL."""
    sqlite_path = Path(os.getenv("SQLITE_PATH", data_dir() / "fomo.sqlite3"))
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Falling back to SQLite database: {sqlite_path}")
    return f"sqlite:///{sqlite_path}"


# Build initial URL
_initial_url = _build_url()
_use_mysql = _initial_url.startswith("mysql")

# Create engine and test connection
ENGINE = create_engine(
    _initial_url,
    pool_pre_ping=True,
    future=True,
)

# If MySQL was configured but connection fails, fall back to SQLite
if _use_mysql:
    if not _test_connection(ENGINE):
        logger.warning("MySQL connection failed, falling back to SQLite")
        DATABASE_URL = _get_sqlite_url()
        ENGINE = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            future=True,
        )
    else:
        DATABASE_URL = _initial_url
        logger.info(f"Successfully connected to MySQL database")
else:
    DATABASE_URL = _initial_url

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
    """Initialize database tables. Handles connection errors gracefully."""
    global DATABASE_URL, ENGINE, SessionLocal
    from .models import Base

    try:
        Base.metadata.create_all(ENGINE)
        logger.info("Database ready (%s)", DATABASE_URL.split("://", 1)[0])
        
        # Migration: Add missing columns
        try:
            with ENGINE.connect() as conn:
                if DATABASE_URL.startswith("sqlite"):
                    # Check user_profiles table for password_hash
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'"
                    ))
                    if result.fetchone():
                        result = conn.execute(text("PRAGMA table_info(user_profiles)"))
                        columns = [row[1] for row in result.fetchall()]
                        if "password_hash" not in columns:
                            logger.info("Adding password_hash column to user_profiles table...")
                            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR(255)"))
                            conn.commit()
                            logger.info("Migration complete: password_hash column added")
                    
                    # Check form_submissions table for user_email
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='form_submissions'"
                    ))
                    if result.fetchone():
                        result = conn.execute(text("PRAGMA table_info(form_submissions)"))
                        columns = [row[1] for row in result.fetchall()]
                        if "user_email" not in columns:
                            logger.info("Adding user_email column to form_submissions table...")
                            conn.execute(text("ALTER TABLE form_submissions ADD COLUMN user_email VARCHAR(255)"))
                            conn.commit()
                            logger.info("Migration complete: user_email column added")
                else:
                    # MySQL/MariaDB
                    # Check user_profiles for password_hash
                    result = conn.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'user_profiles' AND COLUMN_NAME = 'password_hash'"
                    ))
                    if not result.fetchone():
                        logger.info("Adding password_hash column to user_profiles table...")
                        conn.execute(text("ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR(255)"))
                        conn.commit()
                        logger.info("Migration complete: password_hash column added")
                    
                    # Check form_submissions for user_email
                    result = conn.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'form_submissions' AND COLUMN_NAME = 'user_email'"
                    ))
                    if not result.fetchone():
                        logger.info("Adding user_email column to form_submissions table...")
                        conn.execute(text("ALTER TABLE form_submissions ADD COLUMN user_email VARCHAR(255)"))
                        conn.commit()
                        logger.info("Migration complete: user_email column added")
        except Exception as migration_error:
            logger.warning(f"Migration check failed (may already exist): {migration_error}")
            
    except OperationalError as e:
        # If MySQL connection fails during init, try SQLite fallback
        if DATABASE_URL.startswith("mysql"):
            logger.warning(f"MySQL connection failed during init: {e}")
            logger.info("Falling back to SQLite...")
            
            DATABASE_URL = _get_sqlite_url()
            ENGINE = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                future=True,
            )
            SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
            
            # Retry with SQLite
            Base.metadata.create_all(ENGINE)
            logger.info("Database ready (SQLite fallback)")
        else:
            raise


__all__ = ["get_session", "init_db", "ENGINE"]

