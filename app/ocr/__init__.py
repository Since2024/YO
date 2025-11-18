"""OCR fallback package."""

from .extractor import extract_fields_with_ocr, OCRFallbackError

__all__ = ["extract_fields_with_ocr", "OCRFallbackError"]

