"""SQLAlchemy data models for the Auto Form Fill MVP."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FormSubmission(Base):
    """Persisted record of a processed form."""

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
