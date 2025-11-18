"""SQLAlchemy models for storing completed runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(255), nullable=False)
    template_file = Column(String(255), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    gemini_json = Column(Text, nullable=False)
    normalized_fields = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "template_file": self.template_file,
            "pdf_path": self.pdf_path,
            "created_at": self.created_at.isoformat(),
        }


__all__ = ["Base", "FormSubmission"]

