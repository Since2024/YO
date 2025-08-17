"""
Database connection and setup for SmartForm.

Handles database initialization, connection management, and session handling.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from .models import Base


class DatabaseManager:
    """Database manager for SmartForm application."""
    
    def __init__(self, database_url=None):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLAlchemy database URL. If None, uses default SQLite.
        """
        if database_url is None:
            # Default SQLite database in database/ directory
            db_path = os.path.join(os.path.dirname(__file__), 'smartform.db')
            database_url = f"sqlite:///{db_path}"
        
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup SQLAlchemy engine with appropriate configuration."""
        if self.database_url.startswith('sqlite'):
            # SQLite specific configuration
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False  # Set to True for SQL debugging
            )
        else:
            # Other databases (PostgreSQL, MySQL, etc.)
            self.engine = create_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        print("✅ Database tables created successfully")
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)
        print("⚠️  All database tables dropped")
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    @contextmanager
    def get_db_session(self):
        """
        Context manager for database sessions.
        
        Usage:
            with db_manager.get_db_session() as session:
                # Use session for database operations
                pass
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def check_connection(self):
        """Check if database connection is working."""
        try:
            with self.get_db_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def get_database_info(self):
        """Get database information and statistics."""
        try:
            with self.get_db_session() as session:
                # Get table information
                tables = Base.metadata.tables.keys()
                
                # Get record counts
                counts = {}
                for table_name in tables:
                    table = Base.metadata.tables[table_name]
                    count = session.query(table).count()
                    counts[table_name] = count
                
                return {
                    'database_url': self.database_url,
                    'tables': list(tables),
                    'record_counts': counts,
                    'connection_status': 'Connected'
                }
        except Exception as e:
            return {
                'database_url': self.database_url,
                'error': str(e),
                'connection_status': 'Failed'
            }


# Global database manager instance
_db_manager = None


def init_db(database_url=None):
    """
    Initialize the global database manager.
    
    Args:
        database_url: SQLAlchemy database URL
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_db():
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager: Database manager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_manager


def get_db_session():
    """
    Get a new database session.
    
    Returns:
        Session: SQLAlchemy session
        
    Raises:
        RuntimeError: If database not initialized
    """
    return get_db().get_session()


def create_tables():
    """Create all database tables."""
    return get_db().create_tables()


def check_connection():
    """Check database connection."""
    return get_db().check_connection()


def get_database_info():
    """Get database information."""
    return get_db().get_database_info()


# Convenience function for Flask integration
def get_db_session_flask():
    """
    Get database session for Flask applications.
    
    Returns:
        Session: SQLAlchemy session
    """
    db = get_db()
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
