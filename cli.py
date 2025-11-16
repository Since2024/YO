#!/usr/bin/env python3
"""CLI entrypoint for batch processing of form images."""

import argparse
import json
import sys
from pathlib import Path
from typing import List
from uuid import uuid4

from filler.form_filler import FormFiller
from ocr.extractor import OCRExtractor
from printer.pdf_generator import PDFGenerator
from utils.logger import get_logger

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output" / "generated"

logger = get_logger("cli")


def process_image(image_path: Path, template_path: Path, output_dir: Path,
                 mode: str = "bbox", debug: bool = False) -> dict:
    """
    Process a single image through the OCR pipeline.
    
    Args:
        image_path: Path to input image
        template_path: Path to template JSON
        output_dir: Output directory for generated files
        mode: Extraction mode ("bbox" or "semantic")
        debug: Enable debug mode
        
    Returns:
        Dict with processing results
    """
    logger.info(f"Processing image: {image_path}")
    
    try:
        # Load template
        form_filler = FormFiller()
        template = form_filler.load_template(str(template_path))
        
        # Initialize OCR extractor
        extractor = OCRExtractor(languages="nep+eng", use_gpu=False, debug=debug)
        
        # Extract fields
        if mode == "semantic":
            logger.info("Using semantic matching mode")
            extracted = form_filler.extract_and_match_semantically(
                str(image_path),
                template,
                extractor,
                save_mapping=str(output_dir / f"{image_path.stem}_mapping.json")
            )
        else:
            logger.info("Using bbox-based extraction mode")
            extracted = extractor.extract_from_template(str(image_path), template)
        
        # Validate
        validation = form_filler.validate_extracted_data(extracted, template)
        
        # Prepare for PDF
        pdf_data = form_filler.prepare_data_for_pdf(extracted, template)
        
        # Get template image
        metadata = template.get("forms", [{}])[0].get("metadata", {}) if "forms" in template else template.get("metadata", {})
        template_image = metadata.get("image_filename")
        if template_image:
            template_image_path = TEMPLATES_DIR / template_image
        else:
            template_image_path = image_path
        
        # Generate PDF
        pdf_path = output_dir / f"{image_path.stem}_{uuid4().hex[:8]}.pdf"
        pdf_generator = PDFGenerator()
        pdf_generator.create_filled_pdf(
            str(template_image_path),
            pdf_data,
            str(pdf_path),
            dpi=300
        )
        
        # Save JSON
        json_path = output_dir / f"{image_path.stem}_{uuid4().hex[:8]}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "image_path": str(image_path),
                "template": str(template_path),
                "extracted_fields": extracted,
                "validation": validation,
                "pdf_path": str(pdf_path)
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Processed: {image_path.name} -> {pdf_path.name}")
        
        return {
            "success": True,
            "image": str(image_path),
            "pdf": str(pdf_path),
            "json": str(json_path),
            "validation": validation
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to process {image_path}: {e}")
        return {
            "success": False,
            "image": str(image_path),
            "error": str(e)
        }


def process_folder(folder_path: Path, template_path: Path, output_dir: Path,
                   mode: str = "bbox", debug: bool = False) -> List[dict]:
    """Process all images in a folder."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
    image_files = [f for f in folder_path.iterdir() 
                   if f.suffix.lower() in image_extensions and f.is_file()]
    
    if not image_files:
        logger.warning(f"No image files found in {folder_path}")
        return []
    
    logger.info(f"Found {len(image_files)} images to process")
    results = []
    
    for image_file in sorted(image_files):
        result = process_image(image_file, template_path, output_dir, mode, debug)
        results.append(result)
    
    return results


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="OCR-based automatic form filling for Nepali government forms"
    )
    parser.add_argument(
        "--images",
        nargs="+",
        help="One or more image file paths to process"
    )
    parser.add_argument(
        "--folder",
        help="Process all images in a folder"
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Path to template JSON file"
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        help="Output directory for generated PDFs and JSONs (default: output/generated)"
    )
    parser.add_argument(
        "--mode",
        choices=["bbox", "semantic"],
        default="bbox",
        help="Extraction mode: bbox (template-based) or semantic (matching)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (saves debug images and raw OCR JSON)"
    )
    
    args = parser.parse_args()
    
    # Validate template
    template_path = Path(args.template)
    if not template_path.exists():
        logger.error(f"Template not found: {template_path}")
        sys.exit(1)
    
    # Setup output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # Process images
    if args.images:
        for image_path_str in args.images:
            image_path = Path(image_path_str)
            if not image_path.exists():
                logger.error(f"Image not found: {image_path}")
                continue
            result = process_image(image_path, template_path, output_dir, args.mode, args.debug)
            results.append(result)
    
    # Process folder
    elif args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists() or not folder_path.is_dir():
            logger.error(f"Folder not found: {folder_path}")
            sys.exit(1)
        results = process_folder(folder_path, template_path, output_dir, args.mode, args.debug)
    
    else:
        parser.error("Must provide either --images or --folder")
    
    # Summary
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing complete: {successful} successful, {failed} failed")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"{'='*60}")
    
    # Exit with error code if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()

