"""Database package for MySQL integration."""

from .connection import get_db_connection, init_database, close_connection
from .models import (
    FormTemplate,
    FormProcessing,
    ExtractedData,
    OCRSubmission,
    create_tables,
    drop_tables
)

__all__ = [
    'get_db_connection',
    'init_database',
    'close_connection',
    'FormTemplate',
    'FormProcessing',
    'ExtractedData',
    'OCRSubmission',
    'create_tables',
    'drop_tables'
]
