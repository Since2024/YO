#!/usr/bin/env python3
"""Smoke test for Auto Form Fill pipeline."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from utils.logger import setup_logger
from ocr.extractor import OCRExtractor
from filler.form_filler import FormFiller
from printer.pdf_generator import PDFGenerator
from db import init_database, test_connection

load_dotenv()
logger = setup_logger('smoke_test')


def test_database_connection():
    """Test database connection."""
    logger.info("Testing database connection...")
    try:
        init_database()
        if test_connection():
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.warning("⚠️  Database connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


def test_ocr_initialization():
    """Test OCR engine initialization."""
    logger.info("Testing OCR engine initialization...")
    try:
        ocr = OCRExtractor(languages=['en', 'hi'], debug=False)
        logger.info("✅ OCR engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ OCR initialization failed: {e}")
        return False


def test_template_loading():
    """Test template loading."""
    logger.info("Testing template loading...")
    try:
        filler = FormFiller()
        template_path = "/app/templates/business_tax_front.json"
        
        if not os.path.exists(template_path):
            logger.warning(f"⚠️  Template not found: {template_path}")
            return False
        
        template = filler.load_template(template_path)
        logger.info(f"✅ Template loaded: {len(template.get('forms', [{}])[0].get('fields', []))} fields")
        return True
    except Exception as e:
        logger.error(f"❌ Template loading failed: {e}")
        return False


def test_end_to_end_pipeline():
    """Test complete end-to-end pipeline."""
    logger.info("Testing end-to-end pipeline...")
    
    try:
        # Setup
        image_path = "/app/templates/business_front.jpg"
        template_path = "/app/templates/business_tax_front.json"
        output_path = "/app/data/output/test_output.pdf"
        
        if not os.path.exists(image_path):
            logger.warning(f"⚠️  Test image not found: {image_path}")
            return False
        
        # Step 1: Load template
        filler = FormFiller()
        template = filler.load_template(template_path)
        
        # Step 2: Initialize OCR
        ocr = OCRExtractor(languages=['en', 'hi'], debug=False)
        
        # Step 3: Extract data
        extracted_data = ocr.extract_from_template(image_path, template)
        logger.info(f"  Extracted {len(extracted_data)} fields")
        
        # Step 4: Validate data
        validation = filler.validate_extracted_data(extracted_data, template)
        logger.info(f"  Validation: {validation['valid']}")
        
        # Step 5: Prepare for PDF
        pdf_data = filler.prepare_data_for_pdf(extracted_data, template)
        
        # Step 6: Generate PDF
        pdf_gen = PDFGenerator()
        pdf_gen.create_filled_pdf_from_image(image_path, pdf_data, output_path)
        
        # Check output
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ End-to-end pipeline successful. Output: {output_path} ({file_size} bytes)")
            return True
        else:
            logger.error("❌ Output PDF not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ End-to-end pipeline failed: {e}")
        import traceback
        traceback.print_exc()
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
        "End-to-End Pipeline": test_end_to_end_pipeline()
    }
    
    print("\n" + "=" * 70)
    print("Test Results Summary:")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 70)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
