"""OCR package with support for Tesseract and PaddleOCR."""

try:
    from .paddle_extractor import PaddleOCRExtractor
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCRExtractor = None

from .extractor import OCRExtractor as TesseractOCRExtractor, TesseractExtractor

# Default to PaddleOCR for better Nepali support, fallback to Tesseract
if PADDLEOCR_AVAILABLE:
    OCRExtractor = PaddleOCRExtractor
else:
    OCRExtractor = TesseractExtractor

__all__ = ['OCRExtractor', 'TesseractExtractor', 'TesseractOCRExtractor', 'PaddleOCRExtractor', 'PADDLEOCR_AVAILABLE']
