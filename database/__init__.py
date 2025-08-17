"""
Database package for SmartForm OCR system.

This package handles all database operations including:
- Database connection and setup
- SQLAlchemy models
- Database migrations
- Data persistence for templates, processing history, and extracted data
"""

from .database import init_db, get_db
from .models import User, Template, FormProcessing, FormData, ProcessingLog

__all__ = [
    'init_db',
    'get_db', 
    'User',
    'Template',
    'FormProcessing',
    'FormData',
    'ProcessingLog'
]
