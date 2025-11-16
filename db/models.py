"""SQLAlchemy data models for the Auto Form Fill MVP."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class FormTemplate(Base):
    """Form template definitions."""
    
    __tablename__ = "form_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template_json = Column(Text, nullable=False)  # JSON template content
    image_filename = Column(String(500), nullable=True)
    version = Column(String(50), nullable=True, default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    submissions = relationship("Submission", back_populates="template")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template_json": self.template_json,
            "image_filename": self.image_filename,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Submission(Base):
    """Form submission records."""
    
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    pdf_path = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, completed, error
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("FormTemplate", back_populates="submissions")
    extracted_fields = relationship("ExtractedField", back_populates="submission", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "image_path": self.image_path,
            "pdf_path": self.pdf_path,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExtractedField(Base):
    """Individual extracted field data."""
    
    __tablename__ = "extracted_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    field_id = Column(String(100), nullable=False)
    field_name = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    submission = relationship("Submission", back_populates="extracted_fields")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "field_id": self.field_id,
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
        }


# Legacy model for backward compatibility
class FormSubmission(Base):
    """Legacy persisted record of a processed form (kept for backward compatibility)."""

    __tablename__ = "ocr_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_name = Column(String(255), nullable=False)
    template_id = Column(String(255), nullable=False)
    image_path = Column(String(500), nullable=False)
    pdf_path = Column(String(500), nullable=True)
    fields_json = Column(Text, nullable=False)
    validation_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "form_name": self.form_name,
            "template_id": self.template_id,
            "image_path": self.image_path,
            "pdf_path": self.pdf_path,
            "fields_json": self.fields_json,
            "validation_json": self.validation_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
