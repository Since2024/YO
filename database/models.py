"""
SQLAlchemy models for SmartForm database.

Defines the database schema for:
- Users (authentication and authorization)
- Templates (form template storage)
- Form Processing (processing history)
- Form Data (extracted OCR data)
- Processing Logs (detailed processing logs)
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')  # admin, user, guest
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    form_processings = relationship("FormProcessing", back_populates="user")
    created_templates = relationship("Template", back_populates="creator")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Template(Base):
    """Template model for storing form templates."""
    
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    form_type = Column(String(50), nullable=False)  # business_tax, land_tax, etc.
    fields = Column(JSON, nullable=False)  # Store field coordinates and config
    file_path = Column(String(255))  # Path to template file
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="created_templates")
    form_processings = relationship("FormProcessing", back_populates="template")
    
    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', form_type='{self.form_type}')>"


class FormProcessing(Base):
    """Form processing history and tracking."""
    
    __tablename__ = 'form_processings'
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('templates.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    input_file_path = Column(String(255), nullable=False)
    output_file_path = Column(String(255))
    extracted_data = Column(JSON)  # Store OCR results
    processing_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    confidence_score = Column(Float)
    processing_time = Column(Float)  # Processing time in seconds
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    template = relationship("Template", back_populates="form_processings")
    user = relationship("User", back_populates="form_processings")
    form_data = relationship("FormData", back_populates="processing")
    processing_logs = relationship("ProcessingLog", back_populates="processing")
    
    def __repr__(self):
        return f"<FormProcessing(id={self.id}, status='{self.processing_status}', template_id={self.template_id})>"


class FormData(Base):
    """Extracted form data from OCR processing."""
    
    __tablename__ = 'form_data'
    
    id = Column(Integer, primary_key=True)
    processing_id = Column(Integer, ForeignKey('form_processings.id'), nullable=False)
    field_name = Column(String(100), nullable=False)
    extracted_text = Column(Text)
    confidence_score = Column(Float)
    field_type = Column(String(50))  # text, number, date, etc.
    field_coordinates = Column(JSON)  # x, y, width, height
    is_corrected = Column(Boolean, default=False)
    corrected_text = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    processing = relationship("FormProcessing", back_populates="form_data")
    
    def __repr__(self):
        return f"<FormData(id={self.id}, field='{self.field_name}', text='{self.extracted_text[:20]}...')>"


class ProcessingLog(Base):
    """Detailed processing logs for debugging and monitoring."""
    
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True)
    processing_id = Column(Integer, ForeignKey('form_processings.id'), nullable=False)
    log_level = Column(String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    details = Column(JSON)  # Additional log details
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    processing = relationship("FormProcessing", back_populates="processing_logs")
    
    def __repr__(self):
        return f"<ProcessingLog(id={self.id}, level='{self.log_level}', message='{self.message[:50]}...')>"


# Additional models for future enhancements
class SystemConfig(Base):
    """System configuration settings."""
    
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value}')>"


class Analytics(Base):
    """Analytics and reporting data."""
    
    __tablename__ = 'analytics'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float)
    metric_data = Column(JSON)  # Additional metric data
    date_recorded = Column(DateTime, default=func.now())
    period = Column(String(20))  # daily, weekly, monthly
    
    def __repr__(self):
        return f"<Analytics(metric='{self.metric_name}', value={self.metric_value})>"
