"""Database connection management for MySQL."""

import os
import pymysql
from typing import Optional
from contextlib import contextmanager
from pymysql.cursors import DictCursor
from utils.logger import get_logger

logger = get_logger(__name__)

# Global connection pool
_connection = None


def get_connection_params() -> dict:
    """
    Get MySQL connection parameters from environment variables.
    
    Returns:
        dict: Connection parameters
    """
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DB', 'auto_form_fill'),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor
    }


def create_database_if_not_exists() -> None:
    """
    Create the database if it doesn't exist.
    """
    params = get_connection_params()
    db_name = params.pop('database')
    
    try:
        # Connect without specifying database
        conn = pymysql.connect(**params)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Database '{db_name}' checked/created successfully")
        
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise


def get_db_connection():
    """
    Get a MySQL database connection.
    
    Returns:
        pymysql.Connection: Database connection
    """
    global _connection
    
    try:
        # Check if connection exists and is alive
        if _connection is not None:
            _connection.ping(reconnect=True)
            return _connection
        
        # Create new connection
        params = get_connection_params()
        _connection = pymysql.connect(**params)
        logger.info("Database connection established")
        return _connection
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


@contextmanager
def get_db_cursor(commit: bool = True):
    """
    Context manager for database cursor operations.
    
    Args:
        commit: Whether to commit changes after operation
        
    Yields:
        pymysql.cursors.DictCursor: Database cursor
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        cursor.close()


def init_database() -> None:
    """
    Initialize the database and create tables if they don't exist.
    """
    logger.info("Initializing database...")
    
    # Create database if not exists
    create_database_if_not_exists()
    
    # Import models and create tables
    from .models import create_tables
    create_tables()
    
    logger.info("Database initialization completed")


def close_connection() -> None:
    """
    Close the database connection.
    """
    global _connection
    
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Database connection closed")


def test_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
