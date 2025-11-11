"""Database models for MySQL."""

from typing import Optional, Dict, Any, List
import json
from datetime import datetime
from .connection import get_db_cursor
from utils.logger import get_logger

logger = get_logger(__name__)


class FormTemplate:
    """Model for form templates."""
    
    @staticmethod
    def create(name: str, form_type: str, template_path: str, 
               fields_json: str, description: Optional[str] = None) -> int:
        """
        Create a new form template.
        
        Args:
            name: Template name
            form_type: Type of form (business_tax, land_tax, etc.)
            template_path: Path to template JSON file
            fields_json: JSON string of fields configuration
            description: Optional description
            
        Returns:
            int: Inserted template ID
        """
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO form_templates 
                (name, form_type, template_path, fields_json, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (name, form_type, template_path, fields_json, 
                                description, datetime.now()))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(template_id: int) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        with get_db_cursor(commit=False) as cursor:
            sql = "SELECT * FROM form_templates WHERE id = %s"
            cursor.execute(sql, (template_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_by_type(form_type: str) -> List[Dict[str, Any]]:
        """Get all templates of a specific type."""
        with get_db_cursor(commit=False) as cursor:
            sql = "SELECT * FROM form_templates WHERE form_type = %s"
            cursor.execute(sql, (form_type,))
            return cursor.fetchall()
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Get all templates."""
        with get_db_cursor(commit=False) as cursor:
            sql = "SELECT * FROM form_templates ORDER BY created_at DESC"
            cursor.execute(sql)
            return cursor.fetchall()
    
    @staticmethod
    def delete(template_id: int) -> None:
        """Delete a template."""
        with get_db_cursor() as cursor:
            sql = "DELETE FROM form_templates WHERE id = %s"
            cursor.execute(sql, (template_id,))


class FormProcessing:
    """Model for form processing records."""
    
    @staticmethod
    def create(template_id: int, input_file: str, 
               status: str = 'pending') -> int:
        """
        Create a new form processing record.
        
        Args:
            template_id: Template ID used for processing
            input_file: Path to input file
            status: Processing status (pending, processing, completed, failed)
            
        Returns:
            int: Inserted processing ID
        """
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO form_processings 
                (template_id, input_file, status, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (template_id, input_file, status, datetime.now()))
            return cursor.lastrowid
    
    @staticmethod
    def update_status(processing_id: int, status: str, 
                     output_file: Optional[str] = None,
                     error_message: Optional[str] = None,
                     processing_time: Optional[float] = None) -> None:
        """
        Update processing status.
        
        Args:
            processing_id: Processing record ID
            status: New status
            output_file: Path to output file (optional)
            error_message: Error message if failed (optional)
            processing_time: Processing time in seconds (optional)
        """
        with get_db_cursor() as cursor:
            sql = """
                UPDATE form_processings 
                SET status = %s, output_file = %s, error_message = %s,
                    processing_time = %s, updated_at = %s
                WHERE id = %s
            """
            cursor.execute(sql, (status, output_file, error_message, 
                                processing_time, datetime.now(), processing_id))
    
    @staticmethod
    def get_by_id(processing_id: int) -> Optional[Dict[str, Any]]:
        """Get processing record by ID."""
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT fp.*, ft.name as template_name, ft.form_type
                FROM form_processings fp
                JOIN form_templates ft ON fp.template_id = ft.id
                WHERE fp.id = %s
            """
            cursor.execute(sql, (processing_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_all(limit: int = 100) -> List[Dict[str, Any]]:
        """Get all processing records."""
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT fp.*, ft.name as template_name, ft.form_type
                FROM form_processings fp
                JOIN form_templates ft ON fp.template_id = ft.id
                ORDER BY fp.created_at DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    
    @staticmethod
    def get_by_status(status: str) -> List[Dict[str, Any]]:
        """Get processing records by status."""
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT fp.*, ft.name as template_name, ft.form_type
                FROM form_processings fp
                JOIN form_templates ft ON fp.template_id = ft.id
                WHERE fp.status = %s
                ORDER BY fp.created_at DESC
            """
            cursor.execute(sql, (status,))
            return cursor.fetchall()


class ExtractedData:
    """Model for extracted OCR data."""
    
    @staticmethod
    def create(processing_id: int, field_name: str, field_value: str,
               confidence: float, field_type: Optional[str] = None) -> int:
        """
        Create an extracted data record.
        
        Args:
            processing_id: Processing record ID
            field_name: Name of the extracted field
            field_value: Extracted value
            confidence: OCR confidence score
            field_type: Type of field (optional)
            
        Returns:
            int: Inserted data ID
        """
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO extracted_data 
                (processing_id, field_name, field_value, confidence, field_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (processing_id, field_name, field_value, 
                                confidence, field_type, datetime.now()))
            return cursor.lastrowid
    
    @staticmethod
    def bulk_create(processing_id: int, data_list: List[Dict[str, Any]]) -> None:
        """
        Bulk insert extracted data records.
        
        Args:
            processing_id: Processing record ID
            data_list: List of data dictionaries with keys: field_name, field_value, confidence
        """
        if not data_list:
            return
        
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO extracted_data 
                (processing_id, field_name, field_value, confidence, field_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = [
                (processing_id, data['field_name'], data['field_value'],
                 data.get('confidence', 0.0), data.get('field_type'), datetime.now())
                for data in data_list
            ]
            cursor.executemany(sql, values)
    
    @staticmethod
    def get_by_processing_id(processing_id: int) -> List[Dict[str, Any]]:
        """Get all extracted data for a processing record."""
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT * FROM extracted_data 
                WHERE processing_id = %s
                ORDER BY id
            """
            cursor.execute(sql, (processing_id,))
            return cursor.fetchall()
    
    @staticmethod
    def search(field_name: Optional[str] = None, 
               field_value: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search extracted data.
        
        Args:
            field_name: Field name to search (optional)
            field_value: Field value to search (optional, uses LIKE)
            
        Returns:
            List of matching records
        """
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT ed.*, fp.input_file, ft.name as template_name
                FROM extracted_data ed
                JOIN form_processings fp ON ed.processing_id = fp.id
                JOIN form_templates ft ON fp.template_id = ft.id
                WHERE 1=1
            """
            params = []
            
            if field_name:
                sql += " AND ed.field_name = %s"
                params.append(field_name)
            
            if field_value:
                sql += " AND ed.field_value LIKE %s"
                params.append(f"%{field_value}%")
            
            sql += " ORDER BY ed.created_at DESC LIMIT 100"
            cursor.execute(sql, params)
            return cursor.fetchall()


class OCRSubmission:
    """Model for OCR submissions (simplified storage)."""
    
    @staticmethod
    def create(form_name: str, extracted_data_json: str,
               input_file: str, output_file: Optional[str] = None) -> int:
        """
        Create a new OCR submission record.
        
        Args:
            form_name: Name of the form
            extracted_data_json: JSON string of extracted data
            input_file: Path to input image file
            output_file: Path to output PDF file (optional)
            
        Returns:
            int: Inserted submission ID
        """
        with get_db_cursor() as cursor:
            sql = """
                INSERT INTO ocr_submissions 
                (form_name, extracted_data_json, input_file, output_file, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (form_name, extracted_data_json, input_file, 
                                output_file, datetime.now()))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(submission_id: int) -> Optional[Dict[str, Any]]:
        """Get submission by ID."""
        with get_db_cursor(commit=False) as cursor:
            sql = "SELECT * FROM ocr_submissions WHERE id = %s"
            cursor.execute(sql, (submission_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_all(limit: int = 100) -> List[Dict[str, Any]]:
        """Get all submissions."""
        with get_db_cursor(commit=False) as cursor:
            sql = """
                SELECT * FROM ocr_submissions 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()


def create_tables() -> None:
    """Create all database tables if they don't exist."""
    
    tables = {
        'form_templates': """
            CREATE TABLE IF NOT EXISTS form_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                form_type VARCHAR(100) NOT NULL,
                template_path VARCHAR(500) NOT NULL,
                fields_json TEXT NOT NULL,
                description TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_form_type (form_type),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'form_processings': """
            CREATE TABLE IF NOT EXISTS form_processings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                template_id INT NOT NULL,
                input_file VARCHAR(500) NOT NULL,
                output_file VARCHAR(500),
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                error_message TEXT,
                processing_time FLOAT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES form_templates(id) ON DELETE CASCADE,
                INDEX idx_template_id (template_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'extracted_data': """
            CREATE TABLE IF NOT EXISTS extracted_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                processing_id INT NOT NULL,
                field_name VARCHAR(255) NOT NULL,
                field_value TEXT,
                confidence FLOAT,
                field_type VARCHAR(50),
                created_at DATETIME NOT NULL,
                FOREIGN KEY (processing_id) REFERENCES form_processings(id) ON DELETE CASCADE,
                INDEX idx_processing_id (processing_id),
                INDEX idx_field_name (field_name),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'ocr_submissions': """
            CREATE TABLE IF NOT EXISTS ocr_submissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                form_name VARCHAR(255) NOT NULL,
                extracted_data_json TEXT NOT NULL,
                input_file VARCHAR(500) NOT NULL,
                output_file VARCHAR(500),
                created_at DATETIME NOT NULL,
                INDEX idx_form_name (form_name),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    }
    
    with get_db_cursor() as cursor:
        for table_name, create_sql in tables.items():
            try:
                cursor.execute(create_sql)
                logger.info(f"Table '{table_name}' checked/created successfully")
            except Exception as e:
                logger.error(f"Failed to create table '{table_name}': {e}")
                raise


def drop_tables() -> None:
    """Drop all database tables. Use with caution!"""
    
    tables = ['ocr_submissions', 'extracted_data', 'form_processings', 'form_templates']
    
    with get_db_cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table_name in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.warning(f"Table '{table_name}' dropped")
            except Exception as e:
                logger.error(f"Failed to drop table '{table_name}': {e}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
