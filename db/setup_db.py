#!/usr/bin/env python3
"""Database setup script to create tables and initialize schema."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from db.connection import init_db, get_engine
from db.models import Base, FormTemplate, Submission, ExtractedField
from utils.logger import get_logger

logger = get_logger("setup_db")


def setup_database():
    """Create all database tables."""
    logger.info("Setting up database tables...")
    
    try:
        init_db()
        logger.info("✅ Database tables created successfully")
        
        # Verify tables exist
        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Created tables: {', '.join(tables)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False


if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)

