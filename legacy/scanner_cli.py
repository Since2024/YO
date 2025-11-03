#!/usr/bin/env python3
"""
Scanner and Overlay CLI Tool

Dedicated command-line interface for scanner integration and overlay operations.
Provides comprehensive scanner management and overlay processing capabilities.
"""

import argparse
import sys
import json
from typing import Optional, Dict, Any

from filler.scanner_integration import ScannerService
from filler.overlay_system import OverlayService
from filler.ocr import OCRExtractor
from filler.template_loader import TemplateLoader
from filler.preprocess import PreprocessorService


def setup_arguments() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="FirstChild: Scanner and Overlay Management Tool",
        epilog="Example: python scanner_cli.py scan --template templates/business_tax.json --output scanned_form.pdf"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scanner commands
    scan_parser = subparsers.add_parser('scan', help='Scan physical documents')
    scan_parser.add_argument('--scanner', '-s', type=str, help='Scanner device name')
    scan_parser.add_argument('--dpi', type=int, default=300, help='Scanning resolution')
    scan_parser.add_argument('--mode', choices=['color', 'gray', 'lineart'], default='color', help='Color mode')
    scan_parser.add_argument('--output', '-o', type=str, help='Output file path')
    scan_parser.add_argument('--multi-page', action='store_true', help='Scan multiple pages')
    
    list_parser = subparsers.add_parser('list-scanners', help='List available scanners')
    
    test_parser = subparsers.add_parser('test-scanner', help='Test scanner functionality')
    test_parser.add_argument('--scanner', '-s', type=str, help='Scanner device name')
    
    # Overlay commands
    overlay_parser = subparsers.add_parser('overlay', help='Create overlay on form')
    overlay_parser.add_argument('--input', '-i', required=True, type=str, help='Input form image')
    overlay_parser.add_argument('--template', '-t', required=True, type=str, help='OCR template')
    overlay_parser.add_argument('--overlay-template', '-ot', type=str, help='Overlay template name')
    overlay_parser.add_argument('--output', '-o', required=True, type=str, help='Output file path')
    overlay_parser.add_argument('--lang', '-l', default='eng', type=str, help='OCR language')
    
    scan_overlay_parser = subparsers.add_parser('scan-overlay', help='Scan and overlay in one operation')
    scan_overlay_parser.add_argument('--scanner', '-s', type=str, help='Scanner device name')
    scan_overlay_parser.add_argument('--template', '-t', required=True, type=str, help='OCR template')
    scan_overlay_parser.add_argument('--overlay-template', '-ot', type=str, help='Overlay template name')
    scan_overlay_parser.add_argument('--output', '-o', required=True, type=str, help='Output file path')
    scan_overlay_parser.add_argument('--lang', '-l', default='eng', type=str, help='OCR language')
    
    list_overlay_parser = subparsers.add_parser('list-overlays', help='List available overlay templates')
    
    create_overlay_parser = subparsers.add_parser('create-overlay', help='Create new overlay template')
    create_overlay_parser.add_argument('--name', '-n', required=True, type=str, help='Template name')
    create_overlay_parser.add_argument('--base-form', '-b', required=True, type=str, help='Base form path')
    create_overlay_parser.add_argument('--fields', '-f', required=True, type=str, help='Fields JSON file')
    
    # Global options
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    
    return parser


def list_scanners() -> None:
    """List available scanners."""
    print("🔍 Scanning for available scanners...")
    scanner_service = ScannerService()
    scanners = scanner_service.get_available_scanners()
    
    if not scanners:
        print("❌ No scanners detected on the system")
        print("\n💡 Troubleshooting:")
        print("  • Ensure scanner is connected and powered on")
        print("  • Install scanner drivers")
        print("  • On Linux: sudo apt-get install sane-utils")
        print("  • On macOS: brew install sane-backends")
        print("  • On Windows: Install scanner manufacturer drivers")
        return
    
    print(f"✅ Found {len(scanners)} scanner(s):")
    for i, scanner in enumerate(scanners, 1):
        print(f"\n{i}. {scanner['name']}")
        print(f"   Type: {scanner['type']}")
        print(f"   Vendor: {scanner['vendor']}")
        print(f"   Description: {scanner['description']}")


def test_scanner(scanner_name: Optional[str] = None) -> None:
    """Test scanner functionality."""
    print("🧪 Testing scanner functionality...")
    scanner_service = ScannerService()
    
    result = scanner_service.test_scanner(scanner_name)
    
    if result['status'] == 'success':
        print("✅ Scanner test successful!")
        print(f"Scanner: {result['scanner']['name']}")
        print(f"Type: {result['scanner']['type']}")
    else:
        print(f"❌ Scanner test failed: {result['message']}")
        print("\n💡 Troubleshooting:")
        print("  • Check scanner connection")
        print("  • Ensure scanner is not in use by another application")
        print("  • Try different scanner if available")


def scan_document(scanner_name: Optional[str], dpi: int, mode: str, 
                 output_path: Optional[str], multi_page: bool) -> None:
    """Scan a document."""
    print("📷 Scanning document...")
    scanner_service = ScannerService(dpi=dpi, color_mode=mode)
    
    try:
        if multi_page:
            print("📄 Multi-page scanning mode")
            files = scanner_service.scan_multiple_pages(scanner_name, output_path)
            print(f"✅ Scanned {len(files)} page(s):")
            for file_path in files:
                print(f"  • {file_path}")
        else:
            file_path = scanner_service.scan_document(scanner_name, output_path)
            print(f"✅ Document scanned: {file_path}")
    except Exception as e:
        print(f"❌ Scanning failed: {e}")
        sys.exit(1)


def list_overlay_templates() -> None:
    """List available overlay templates."""
    print("📋 Available overlay templates:")
    overlay_service = OverlayService()
    templates = overlay_service.get_available_overlay_templates()
    
    if not templates:
        print("❌ No overlay templates found")
        print("💡 Create templates using: python scanner_cli.py create-overlay")
        return
    
    for i, template_name in enumerate(templates, 1):
        print(f"{i}. {template_name}")
        
        # Validate template
        result = overlay_service.validate_overlay_template(template_name)
        if result['status'] == 'success':
            print(f"   ✅ Valid")
        else:
            print(f"   ❌ Invalid: {result['message']}")


def create_overlay_template(name: str, base_form: str, fields_file: str) -> None:
    """Create a new overlay template."""
    print(f"📝 Creating overlay template: {name}")
    
    # Load field configurations
    try:
        with open(fields_file, 'r', encoding='utf-8') as f:
            field_configs = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load fields file: {e}")
        sys.exit(1)
    
    # Create template
    overlay_service = OverlayService()
    try:
        overlay_service.create_overlay_template(name, base_form, field_configs)
        print(f"✅ Overlay template created: {name}")
    except Exception as e:
        print(f"❌ Failed to create template: {e}")
        sys.exit(1)


def process_overlay(input_path: str, template_path: str, overlay_template: Optional[str],
                   output_path: str, language: str) -> None:
    """Process overlay operation."""
    print("🔄 Processing overlay operation...")
    
    # Load OCR template
    template_loader = TemplateLoader()
    template_data = template_loader.load_template(template_path)
    
    # Preprocess input
    preprocessor = PreprocessorService()
    processed_images = preprocessor.process_input(input_path)
    
    # Extract data with OCR
    ocr_extractor = OCRExtractor(language=language)
    extracted_data = {}
    
    for page_num, image in enumerate(processed_images, 1):
        if page_num in [field.get('page', 1) for field in template_data['fields']]:
            page_data = ocr_extractor.extract_from_page(image, template_data, page_num)
            extracted_data.update(page_data)
    
    print(f"✅ Extracted {len(extracted_data)} field(s)")
    
    # Create overlay
    overlay_service = OverlayService()
    overlay_template_name = overlay_template or "business_tax_overlay"
    
    try:
        overlaid_path = overlay_service.overlay_on_digital_form(
            input_path, overlay_template_name, extracted_data, output_path
        )
        print(f"✅ Overlay created: {overlaid_path}")
    except Exception as e:
        print(f"❌ Overlay failed: {e}")
        sys.exit(1)


def scan_and_overlay(scanner_name: Optional[str], template_path: str, 
                    overlay_template: Optional[str], output_path: str, language: str) -> None:
    """Scan document and create overlay in one operation."""
    print("📷 Scanning and overlaying in one operation...")
    
    # Scan document
    scanner_service = ScannerService()
    try:
        scanned_path = scanner_service.scan_document(scanner_name)
        print(f"✅ Document scanned: {scanned_path}")
    except Exception as e:
        print(f"❌ Scanning failed: {e}")
        sys.exit(1)
    
    # Process overlay
    process_overlay(scanned_path, template_path, overlay_template, output_path, language)


def main() -> int:
    """Main application entry point."""
    parser = setup_arguments()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Print header
    print("🔧 FirstChild - Scanner and Overlay Management Tool")
    print("=" * 60)
    
    try:
        if args.command == 'list-scanners':
            list_scanners()
        elif args.command == 'test-scanner':
            test_scanner(args.scanner)
        elif args.command == 'scan':
            scan_document(args.scanner, args.dpi, args.mode, args.output, args.multi_page)
        elif args.command == 'list-overlays':
            list_overlay_templates()
        elif args.command == 'create-overlay':
            create_overlay_template(args.name, args.base_form, args.fields)
        elif args.command == 'overlay':
            process_overlay(args.input, args.template, args.overlay_template, 
                          args.output, args.lang)
        elif args.command == 'scan-overlay':
            scan_and_overlay(args.scanner, args.template, args.overlay_template,
                           args.output, args.lang)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
        
        print("\n🎉 Operation completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
