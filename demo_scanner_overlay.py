#!/usr/bin/env python3
"""
Scanner and Overlay System Demo

Demonstrates the new scanner integration and overlay system capabilities.
Shows how to scan physical documents and overlay extracted data onto forms.
"""

import os
import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from filler.scanner_integration import ScannerService
from filler.overlay_system import OverlayService
from filler.ocr import OCRExtractor
from filler.template_loader import TemplateLoader
from filler.preprocess import PreprocessorService


def create_demo_physical_form() -> str:
    """Create a demo physical form image for testing."""
    print("📝 Creating demo physical form...")
    
    # Create a realistic form image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a realistic font
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw form header
    draw.text((50, 30), "BUSINESS TAX RETURN FORM", fill='black', font=font_large)
    draw.text((50, 60), "Tax Year: 2024", fill='black', font=font_normal)
    draw.text((50, 80), "Form ID: BT-2024-001", fill='black', font=font_small)
    
    # Draw form fields with labels
    fields = [
        (50, 150, "Business Name:", "ABC Manufacturing Corp"),
        (50, 200, "Tax ID:", "12-3456789"),
        (50, 250, "Business Address:", "123 Industrial Blvd"),
        (50, 300, "City, State, ZIP:", "Chicago, IL 60601"),
        (50, 350, "Annual Revenue:", "$2,500,000"),
        (50, 400, "Total Expenses:", "$1,800,000"),
        (50, 450, "Net Income:", "$700,000")
    ]
    
    for x, y, label, value in fields:
        # Draw label
        draw.text((x, y), label, fill='black', font=font_normal)
        # Draw value (simulating handwritten/typed text)
        draw.text((x + 200, y), value, fill='darkblue', font=font_normal)
    
    # Draw form boundaries
    draw.rectangle([30, 20, width-30, height-30], outline='black', width=2)
    
    # Save the form
    os.makedirs('input/demo', exist_ok=True)
    form_path = 'input/demo/physical_business_tax_form.png'
    image.save(form_path, 'PNG')
    print(f"✅ Demo physical form created: {form_path}")
    
    return form_path


def demo_scanner_functionality() -> None:
    """Demonstrate scanner functionality."""
    print("\n" + "="*60)
    print("📷 SCANNER FUNCTIONALITY DEMO")
    print("="*60)
    
    # Initialize scanner service
    scanner_service = ScannerService()
    
    # List available scanners
    print("\n1. Listing available scanners...")
    scanners = scanner_service.get_available_scanners()
    
    if not scanners:
        print("❌ No scanners detected")
        print("💡 This is expected if no scanner is connected")
        print("   The system will still work with existing image files")
        return
    
    print(f"✅ Found {len(scanners)} scanner(s):")
    for scanner in scanners:
        print(f"  • {scanner['name']} ({scanner['type']})")
    
    # Test scanner functionality
    print("\n2. Testing scanner functionality...")
    test_result = scanner_service.test_scanner()
    
    if test_result['status'] == 'success':
        print("✅ Scanner test successful!")
        print(f"   Scanner: {test_result['scanner']['name']}")
    else:
        print(f"❌ Scanner test failed: {test_result['message']}")
        print("   This is normal if no scanner is connected")


def demo_overlay_functionality() -> None:
    """Demonstrate overlay functionality."""
    print("\n" + "="*60)
    print("🖼️  OVERLAY FUNCTIONALITY DEMO")
    print("="*60)
    
    # Create demo physical form
    form_path = create_demo_physical_form()
    
    # Initialize services
    overlay_service = OverlayService()
    template_loader = TemplateLoader()
    preprocessor = PreprocessorService()
    ocr_extractor = OCRExtractor()
    
    # Load OCR template
    print("\n1. Loading OCR template...")
    template_data = template_loader.load_template('templates/business_tax.json')
    print("✅ OCR template loaded")
    
    # Process the form
    print("\n2. Processing form with OCR...")
    processed_images = preprocessor.process_input(form_path)
    
    # Extract data
    extracted_data = {}
    for page_num, image in enumerate(processed_images, 1):
        if page_num in [field.get('page', 1) for field in template_data['fields']]:
            page_data = ocr_extractor.extract_from_page(image, template_data, page_num)
            extracted_data.update(page_data)
    
    print(f"✅ Extracted {len(extracted_data)} field(s)")
    
    # Display extracted data
    print("\n3. Extracted Data:")
    for field_name, data in extracted_data.items():
        text = data.get('text', '')[:30]  # Truncate long text
        confidence = data.get('confidence', 0)
        print(f"  • {field_name}: '{text}' (confidence: {confidence:.1f}%)")
    
    # List overlay templates
    print("\n4. Available overlay templates:")
    templates = overlay_service.get_available_overlay_templates()
    
    if not templates:
        print("❌ No overlay templates found")
        print("💡 Creating sample overlay template...")
        create_sample_overlay_template()
        templates = overlay_service.get_available_overlay_templates()
    
    for template_name in templates:
        print(f"  • {template_name}")
    
    # Create overlay
    print("\n5. Creating overlay...")
    overlay_template = templates[0] if templates else "business_tax_overlay"
    
    try:
        output_path = f"output/demo/overlayed_form_demo.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        overlaid_path = overlay_service.overlay_on_digital_form(
            form_path, overlay_template, extracted_data, output_path
        )
        print(f"✅ Overlay created: {overlaid_path}")
        
    except Exception as e:
        print(f"❌ Overlay failed: {e}")
        print("💡 This might be due to missing overlay template")


def create_sample_overlay_template() -> None:
    """Create a sample overlay template for demo."""
    print("📝 Creating sample overlay template...")
    
    overlay_service = OverlayService()
    
    # Define field configurations
    field_configs = [
        {
            "name": "business_name",
            "x": 250,
            "y": 150,
            "width": 300,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "tax_id",
            "x": 250,
            "y": 200,
            "width": 150,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "business_address",
            "x": 250,
            "y": 250,
            "width": 350,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "city_state_zip",
            "x": 250,
            "y": 300,
            "width": 350,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "annual_revenue",
            "x": 250,
            "y": 350,
            "width": 120,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "total_expenses",
            "x": 250,
            "y": 400,
            "width": 120,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        },
        {
            "name": "net_income",
            "x": 250,
            "y": 450,
            "width": 120,
            "height": 25,
            "font_size": 12,
            "font_color": "red",
            "alignment": "left"
        }
    ]
    
    # Create template
    overlay_service.create_overlay_template(
        "business_tax_overlay",
        "templates/forms/business_tax_blank.pdf",
        field_configs
    )
    print("✅ Sample overlay template created")


def demo_scan_and_overlay_workflow() -> None:
    """Demonstrate the complete scan-and-overlay workflow."""
    print("\n" + "="*60)
    print("🔄 COMPLETE SCAN-AND-OVERLAY WORKFLOW DEMO")
    print("="*60)
    
    print("\nThis demo shows the complete workflow:")
    print("1. Scan physical document using scanner")
    print("2. Extract data using OCR")
    print("3. Overlay extracted data onto form template")
    print("4. Generate final filled form")
    
    print("\n💡 To test with a real scanner:")
    print("   python scanner_cli.py scan-overlay \\")
    print("     --template templates/business_tax.json \\")
    print("     --overlay-template business_tax_overlay \\")
    print("     --output output/final_form.png")
    
    print("\n💡 To test with existing image:")
    print("   python scanner_cli.py overlay \\")
    print("     --input input/demo/physical_business_tax_form.png \\")
    print("     --template templates/business_tax.json \\")
    print("     --overlay-template business_tax_overlay \\")
    print("     --output output/final_form.png")


def main() -> None:
    """Main demo function."""
    print("🚀 FirstChild - Scanner and Overlay System Demo")
    print("=" * 60)
    print("This demo showcases the new scanner integration and overlay capabilities")
    print("of the FirstChild application.")
    
    try:
        # Demo scanner functionality
        demo_scanner_functionality()
        
        # Demo overlay functionality
        demo_overlay_functionality()
        
        # Demo complete workflow
        demo_scan_and_overlay_workflow()
        
        print("\n" + "="*60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n📁 Generated files:")
        print("  • input/demo/physical_business_tax_form.png")
        print("  • output/demo/overlayed_form_demo.png")
        print("  • templates/overlay/business_tax_overlay.json")
        
        print("\n🔧 Available commands:")
        print("  • python scanner_cli.py list-scanners")
        print("  • python scanner_cli.py test-scanner")
        print("  • python scanner_cli.py scan --output scanned.png")
        print("  • python scanner_cli.py overlay --input form.png --template template.json --output result.png")
        print("  • python scanner_cli.py scan-overlay --template template.json --output result.png")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
