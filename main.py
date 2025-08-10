#!/usr/bin/env python3
"""
FirstChild: OCR-based PDF Form Filling CLI Application

A comprehensive tool for automated form filling using OCR technology.
Extracts data from scanned documents and fills official PDF forms.
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from filler.preprocess import PreprocessorService
from filler.template_loader import TemplateLoader
from filler.ocr import OCRExtractor
from filler.generate_pdf import PDFGenerator


def setup_arguments() -> argparse.ArgumentParser:
    """
    Setup command line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="FirstChild: OCR-based PDF Form Filling Tool",
        epilog="Example: python main.py --input sample.pdf --template templates/business_tax.json --output filled_form.pdf"
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=str,
        help="Path to input PDF or image file"
    )
    
    parser.add_argument(
        "--template", "-t",
        required=True,
        type=str,
        help="Path to JSON template file"
    )
    
    parser.add_argument(
        "--output", "-o",
        required=True,
        type=str,
        help="Path for output filled PDF"
    )
    
    parser.add_argument(
        "--lang", "-l",
        default="eng",
        type=str,
        help="OCR language code (default: eng)"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode with detailed logging"
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
    # Check input file exists
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file '{args.input}' not found")
        return False
    
    # Check template file exists
    if not os.path.exists(args.template):
        print(f"❌ Error: Template file '{args.template}' not found")
        return False
    
    # Validate input file extension
    input_ext = Path(args.input).suffix.lower()
    if input_ext not in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
        print(f"❌ Error: Unsupported input file format '{input_ext}'")
        return False
    
    # Validate template file extension
    if not args.template.endswith('.json'):
        print(f"❌ Error: Template file must be JSON format")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return True


def save_extraction_results(extracted_data: Dict[str, Any], output_path: str) -> None:
    """
    Save OCR extraction results to JSON file for auditing.
    
    Args:
        extracted_data: Dictionary containing extracted OCR data
        output_path: Path for output PDF (used to generate JSON filename)
    """
    json_path = Path(output_path).with_suffix('.json')
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Extraction results saved to: {json_path}")


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    parser = setup_arguments()
    args = parser.parse_args()
    
    # Print header
    print("🔧 FirstChild - OCR-based PDF Form Filling Tool")
    print("=" * 50)
    
    try:
        # Validate inputs
        if not validate_inputs(args):
            return 1
        
        print(f"📁 Input file: {args.input}")
        print(f"📋 Template: {args.template}")
        print(f"💾 Output: {args.output}")
        print(f"🌐 Language: {args.lang}")
        
        # Step 1: Load and validate template
        print("\n🔄 Step 1: Loading template...")
        template_loader = TemplateLoader()
        template_data = template_loader.load_template(args.template)
        template_loader.validate_template(template_data)
        print("✅ Template loaded and validated successfully")
        
        # Step 2: Preprocess input file
        print("\n🔄 Step 2: Preprocessing input file...")
        preprocessor = PreprocessorService()
        processed_images = preprocessor.process_input(args.input)
        print(f"✅ Processed {len(processed_images)} page(s)")
        
        # Step 3: Extract data using OCR
        print("\n🔄 Step 3: Extracting data with OCR...")
        ocr_extractor = OCRExtractor(language=args.lang, debug=args.debug)
        extracted_data = {}
        
        for page_num, image in enumerate(processed_images, 1):
            if page_num in [field.get('page', 1) for field in template_data['fields']]:
                page_data = ocr_extractor.extract_from_page(
                    image, template_data, page_num
                )
                extracted_data.update(page_data)
        
        print(f"✅ Extracted {len(extracted_data)} field(s)")
        
        # Display extracted data
        if args.debug:
            print("\n📊 Extracted Data:")
            for field_name, value in extracted_data.items():
                print(f"  • {field_name}: '{value['text']}'")
        
        # Step 4: Generate filled PDF
        print("\n🔄 Step 4: Generating filled PDF...")
        pdf_generator = PDFGenerator()
        pdf_generator.create_filled_pdf(
            template_data, extracted_data, args.output
        )
        print(f"✅ Filled PDF generated: {args.output}")
        
        # Step 5: Save extraction results for auditing
        print("\n🔄 Step 5: Saving extraction results...")
        save_extraction_results(extracted_data, args.output)
        
        print("\n🎉 Process completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())