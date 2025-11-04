#!/usr/bin/env python3
"""
Auto Form Fill - OCR-based PDF Form Filling CLI Application

A comprehensive tool for automated form filling using PaddleOCR technology.
Extracts data from scanned documents and fills official PDF forms for 
Nepali government forms (Business Tax, Land/Sampati Tax).
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from utils.logger import setup_logger
from ocr.extractor import OCRExtractor
from filler.form_filler import FormFiller
from printer.pdf_generator import PDFGenerator
from db import init_database, FormTemplate, FormProcessing, ExtractedData

# Setup logger
logger = setup_logger()


def setup_arguments() -> argparse.ArgumentParser:
    """
    Setup command line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Auto Form Fill: OCR-based PDF Form Filling Tool for Nepali Government Forms",
        epilog="Example: python main.py --image business_front.jpg --template templates/business_tax_front.json --output filled_form.pdf"
    )
    
    parser.add_argument(
        "--image", "-i",
        required=True,
        type=str,
        help="Path to input form image (JPG/PNG)"
    )
    
    parser.add_argument(
        "--template", "-t",
        required=True,
        type=str,
        help="Path to JSON template file defining form fields"
    )
    
    parser.add_argument(
        "--output", "-o",
        required=True,
        type=str,
        help="Path for output filled PDF"
    )
    
    parser.add_argument(
        "--data",
        type=str,
        help="Path to save extracted data JSON (optional)"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode with detailed logging"
    )
    
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database storage"
    )
    
    parser.add_argument(
        "--languages", "-l",
        default="en,hi",
        type=str,
        help="OCR languages (comma-separated, e.g., 'en,hi' for English and Devanagari)"
    )
    
    return parser


def validate_inputs(args: argparse.Namespace) -> bool:
    """
    Validate input arguments and file paths.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        bool: True if all validations pass
    """
    # Check input image exists
    if not os.path.exists(args.image):
        logger.error(f"Input image not found: {args.image}")
        return False
    
    # Check template file exists
    if not os.path.exists(args.template):
        logger.error(f"Template file not found: {args.template}")
        return False
    
    # Validate input file extension
    input_ext = Path(args.image).suffix.lower()
    if input_ext not in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
        logger.error(f"Unsupported input image format: {input_ext}")
        return False
    
    # Validate template file extension
    if not args.template.endswith('.json'):
        logger.error("Template file must be JSON format")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return True


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    parser = setup_arguments()
    args = parser.parse_args()
    
    # Print header
    print("=" * 70)
    print("🔧 Auto Form Fill - OCR-based PDF Form Filling Tool")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Validate inputs
        logger.info("Validating inputs...")
        if not validate_inputs(args):
            return 1
        
        logger.info(f"📁 Input image: {args.image}")
        logger.info(f"📋 Template: {args.template}")
        logger.info(f"💾 Output: {args.output}")
        logger.info(f"🌐 Languages: {args.languages}")
        
        # Initialize database if not disabled
        if not args.no_db:
            logger.info("\n🔄 Step 1: Initializing database...")
            try:
                init_database()
                logger.info("✅ Database initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️  Database initialization failed: {e}")
                logger.warning("Continuing without database storage...")
                args.no_db = True
        
        # Step 2: Load template
        logger.info("\n🔄 Step 2: Loading form template...")
        form_filler = FormFiller()
        template_data = form_filler.load_template(args.template)
        logger.info("✅ Template loaded successfully")
        
        # Step 3: Initialize OCR
        logger.info("\n🔄 Step 3: Initializing OCR engine...")
        languages = [lang.strip() for lang in args.languages.split(',')]
        ocr_extractor = OCRExtractor(languages=languages, debug=args.debug)
        logger.info("✅ OCR engine initialized")
        
        # Step 4: Extract data from image
        logger.info("\n🔄 Step 4: Extracting data with OCR...")
        extracted_data = ocr_extractor.extract_from_template(args.image, template_data)
        logger.info(f"✅ Extracted {len(extracted_data)} fields")
        
        # Display extracted data summary
        if args.debug:
            logger.info("\n📊 Extracted Data Summary:")
            for field_id, field_data in extracted_data.items():
                logger.info(f"  • {field_data['field_name']}: '{field_data['text']}' "
                          f"(confidence: {field_data['confidence']:.2f})")
        
        # Step 5: Validate extracted data
        logger.info("\n🔄 Step 5: Validating extracted data...")
        validation_result = form_filler.validate_extracted_data(extracted_data, template_data)
        
        if validation_result['errors']:
            logger.warning("⚠️  Validation errors found:")
            for error in validation_result['errors']:
                logger.warning(f"  • {error}")
        
        if validation_result['warnings']:
            logger.info("⚠️  Validation warnings:")
            for warning in validation_result['warnings']:
                logger.info(f"  • {warning}")
        
        if validation_result['valid']:
            logger.info("✅ Validation passed")
        
        # Step 6: Save extracted data JSON
        if args.data:
            data_output_path = args.data
        else:
            data_output_path = str(Path(args.output).with_suffix('.json'))
        
        logger.info("\n🔄 Step 6: Saving extracted data...")
        form_filler.save_extracted_json(extracted_data, data_output_path)
        logger.info(f"✅ Extracted data saved to: {data_output_path}")
        
        # Step 7: Prepare data for PDF
        logger.info("\n🔄 Step 7: Preparing data for PDF generation...")
        pdf_data = form_filler.prepare_data_for_pdf(extracted_data, template_data)
        logger.info(f"✅ Prepared {len(pdf_data)} fields for PDF")
        
        # Step 8: Generate filled PDF
        logger.info("\n🔄 Step 8: Generating filled PDF...")
        pdf_generator = PDFGenerator()
        
        # Use the image as template background
        pdf_generator.create_filled_pdf_from_image(args.image, pdf_data, args.output)
        logger.info(f"✅ Filled PDF generated: {args.output}")
        
        # Step 9: Save to database
        if not args.no_db:
            logger.info("\n🔄 Step 9: Saving to database...")
            try:
                # Create or get template record
                template_name = template_data.get('forms', [{}])[0].get('name', 
                               template_data.get('form', 'Unknown Form'))
                form_type = template_data.get('forms', [{}])[0].get('form_type',
                           template_data.get('form_id', 'unknown'))
                
                # Create processing record
                processing_id = FormProcessing.create(
                    template_id=1,  # Placeholder, should create/get template first
                    input_file=args.image,
                    status='processing'
                )
                
                # Save extracted data
                data_list = [
                    {
                        'field_name': data['field_name'],
                        'field_value': data['text'],
                        'confidence': data['confidence'],
                        'field_type': data.get('field_type')
                    }
                    for data in extracted_data.values()
                ]
                ExtractedData.bulk_create(processing_id, data_list)
                
                # Update processing status
                processing_time = time.time() - start_time
                FormProcessing.update_status(
                    processing_id,
                    status='completed',
                    output_file=args.output,
                    processing_time=processing_time
                )
                
                logger.info("✅ Data saved to database")
            except Exception as e:
                logger.warning(f"⚠️  Failed to save to database: {e}")
        
        # Calculate total time
        total_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        print(f"🎉 Process completed successfully in {total_time:.2f} seconds!")
        print("=" * 70)
        print(f"📄 Filled PDF: {args.output}")
        print(f"📊 Extracted Data: {data_output_path}")
        print("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Process interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
