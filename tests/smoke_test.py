#!/usr/bin/env python3
"""Smoke test for Auto Form Fill pipeline."""

import sys
from pathlib import Path

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.logger import get_logger  # noqa: E402
from ocr.extractor import OCRExtractor  # noqa: E402
from filler.form_filler import FormFiller  # noqa: E402
from printer.pdf_generator import PDFGenerator  # noqa: E402
from db import get_engine, init_db  # noqa: E402

TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output" / "tests"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger("smoke_test")


def test_database_connection():
    """Test database connection."""
    logger.info("Testing database connection...")
    try:
        init_db()
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("❌ Database test failed: %s", exc)
        return False


def test_ocr_initialization():
    """Test OCR engine initialization."""
    logger.info("Testing OCR engine initialization...")
    try:
        OCRExtractor(languages="nep+eng", debug=False)
        logger.info("✅ OCR engine initialized successfully")
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("❌ OCR initialization failed: %s", exc)
        return False


def test_template_loading():
    """Test template loading."""
    logger.info("Testing template loading...")
    try:
        filler = FormFiller()
        template_path = TEMPLATES_DIR / "business_tax_front.json"
        if not template_path.exists():
            logger.warning("⚠️  Template not found: %s", template_path)
            return False
        template = filler.load_template(str(template_path))
        fields = template.get("forms", [{}])[0].get("fields", [])
        logger.info("✅ Template loaded: %d fields", len(fields))
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("❌ Template loading failed: %s", exc)
        return False


def test_end_to_end_pipeline():
    """Test complete end-to-end pipeline."""
    logger.info("Testing end-to-end pipeline...")
    try:
        image_path = TEMPLATES_DIR / "business_front.jpg"
        template_path = TEMPLATES_DIR / "business_tax_front.json"
        output_path = OUTPUT_DIR / "smoke_test.pdf"

        if not image_path.exists():
            logger.warning("⚠️  Test image not found: %s", image_path)
            return False

        filler = FormFiller()
        template = filler.load_template(str(template_path))

        ocr = OCRExtractor(languages="nep+eng", debug=False)
        extracted_data = ocr.extract_from_template(str(image_path), template)
        logger.info("  Extracted %d fields", len(extracted_data))

        validation = filler.validate_extracted_data(extracted_data, template)
        logger.info("  Validation: %s", validation["valid"])

        pdf_data = filler.prepare_data_for_pdf(extracted_data, template)

        pdf_gen = PDFGenerator()
        pdf_gen.create_filled_pdf_from_image(str(image_path), pdf_data, str(output_path))

        if output_path.exists():
            logger.info(
                "✅ End-to-end pipeline successful. Output: %s (%d bytes)",
                output_path,
                output_path.stat().st_size,
            )
            return True
        logger.error("❌ Output PDF not created")
        return False
    except Exception as exc:  # pragma: no cover
        logger.error("❌ End-to-end pipeline failed: %s", exc)
        return False


def run_all_tests():
    """Run all smoke tests."""
    print("\n" + "=" * 70)
    print("          Auto Form Fill - Smoke Test Suite")
    print("=" * 70 + "\n")

    results = {
        "Database Connection": test_database_connection(),
        "OCR Initialization": test_ocr_initialization(),
        "Template Loading": test_template_loading(),
        "End-to-End Pipeline": test_end_to_end_pipeline(),
    }

    print("\n" + "=" * 70)
    print("Test Results Summary:")
    print("=" * 70)

    passed = sum(1 for result in results.values() if result)
    failed = len(results) - passed

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")

    print("=" * 70)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    raise SystemExit(0 if success else 1)
