#!/usr/bin/env python3
"""
Test script for FirstChild application
Creates a sample form image and tests the OCR processing pipeline
"""

from PIL import Image, ImageDraw, ImageFont
import os
import json

def create_sample_form():
    """Create a sample form image for testing"""
    
    # Create a white image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fallback to PIL default if not available
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    # Draw form title
    draw.text((50, 30), "SAMPLE BUSINESS TAX FORM", fill='black', font=font_large)
    draw.text((50, 55), "Tax Year: 2024", fill='black', font=font_normal)
    
    # Draw form fields with sample data
    fields_data = [
        (120, 150, "ABC Manufacturing Corp"),      # business_name
        (450, 150, "12-3456789"),                  # tax_id  
        (120, 200, "123 Industrial Blvd"),        # business_address
        (120, 250, "Chicago, IL 60601"),          # city_state_zip
        (400, 350, "$2,500,000"),                 # annual_revenue
        (400, 400, "$1,800,000"),                 # total_expenses  
        (400, 450, "$700,000"),                   # net_income
        (500, 100, "2024"),                       # tax_year
    ]
    
    # Draw the sample data
    for x, y, text in fields_data:
        draw.text((x, y), text, fill='black', font=font_normal)
    
    # Draw field boundaries for visual reference
    draw.rectangle([120, 145, 420, 170], outline='lightgray', width=1)  # business_name
    draw.rectangle([450, 145, 600, 170], outline='lightgray', width=1)  # tax_id
    draw.rectangle([120, 195, 470, 220], outline='lightgray', width=1)  # business_address
    draw.rectangle([120, 245, 470, 270], outline='lightgray', width=1)  # city_state_zip
    draw.rectangle([400, 345, 520, 370], outline='lightgray', width=1)  # annual_revenue
    draw.rectangle([400, 395, 520, 420], outline='lightgray', width=1)  # total_expenses
    draw.rectangle([400, 445, 520, 470], outline='lightgray', width=1)  # net_income
    draw.rectangle([500, 95, 580, 120], outline='lightgray', width=1)   # tax_year
    
    # Save the image
    os.makedirs('input/samples', exist_ok=True)
    image_path = 'input/samples/sample_business_tax.png'
    image.save(image_path, 'PNG')
    print(f"Sample form image created: {image_path}")
    
    return image_path

def test_ocr_system():
    """Test the OCR system components individually"""
    from filler.ocr import OCRExtractor
    from filler.template_loader import TemplateLoader
    
    print("🧪 Testing OCR System Components...")
    
    # Test OCR installation
    ocr = OCRExtractor()
    test_info = ocr.test_ocr_installation()
    print(f"OCR Installation: {test_info['status']}")
    print(f"Tesseract Version: {test_info.get('version', 'Unknown')}")
    print(f"Available Languages: {', '.join(test_info.get('available_languages', ['Unknown']))}")
    
    # Test template loading
    template_loader = TemplateLoader()
    template_data = template_loader.load_template('templates/business_tax.json')
    print(f"Template loaded: {template_data['name']}")
    print(f"Template fields: {len(template_data['fields'])}")
    
    return test_info['status'] == 'success'

def main():
    """Main test function"""
    print("🚀 FirstChild Application Test")
    print("=" * 40)
    
    # Test system components
    if not test_ocr_system():
        print("❌ OCR system test failed!")
        return 1
    
    # Create sample form
    sample_image = create_sample_form()
    
    # Test the full pipeline
    print("\n🔄 Testing Full Processing Pipeline...")
    
    os.system(f"""
    python main.py \
        --input {sample_image} \
        --template templates/business_tax.json \
        --output output/filled_forms/test_output.pdf \
        --debug
    """)
    
    # Check if output files were created
    if os.path.exists('output/filled_forms/test_output.pdf'):
        print("✅ PDF output generated successfully!")
    else:
        print("❌ PDF output not found!")
    
    if os.path.exists('output/filled_forms/test_output.json'):
        print("✅ JSON extraction results saved!")
        
        # Display extracted data
        with open('output/filled_forms/test_output.json', 'r') as f:
            results = json.load(f)
        
        print("\n📊 Extracted Data Preview:")
        for field_name, data in list(results.items())[:3]:  # Show first 3 fields
            confidence = data.get('confidence', 0)
            text = data.get('text', '')[:30]  # Truncate long text
            print(f"  • {field_name}: '{text}' (confidence: {confidence:.1f}%)")
    else:
        print("❌ JSON extraction results not found!")
    
    print("\n🎉 Test completed! Check the output/ directory for results.")

if __name__ == "__main__":
    main()