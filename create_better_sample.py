#!/usr/bin/env python3
"""
Create a better sample form image with improved contrast for OCR testing
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_high_contrast_sample():
    """Create a high-contrast sample form for better OCR results"""
    
    # Create a larger white image with high resolution
    width, height = 2400, 1800  # Higher resolution for better OCR
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a monospace font for better OCR
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36) 
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except:
        font_title = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    # Draw form background and borders
    draw.rectangle([50, 50, width-50, height-50], outline='black', width=3)
    
    # Draw form title
    draw.text((150, 100), "BUSINESS TAX FORM", fill='black', font=font_title)
    
    # Create field boxes and labels - scaled up 3x from template coordinates
    fields_info = [
        # (x, y, width, height, label, sample_text)
        (360, 450, 900, 75, "Business Name:", "ABC MANUFACTURING CORP"),
        (1350, 450, 450, 75, "Tax ID:", "12-3456789"),
        (360, 600, 1050, 75, "Business Address:", "123 INDUSTRIAL BLVD"),
        (360, 750, 1050, 75, "City, State, ZIP:", "CHICAGO, IL 60601"),
        (1200, 1050, 360, 75, "Annual Revenue:", "$2,500,000"),
        (1200, 1200, 360, 75, "Total Expenses:", "$1,800,000"),
        (1200, 1350, 360, 75, "Net Income:", "$700,000"),
        (1500, 300, 240, 75, "Tax Year:", "2024"),
    ]
    
    # Draw each field
    for x, y, w, h, label, sample_text in fields_info:
        # Draw field border
        draw.rectangle([x-5, y-5, x+w+5, y+h+5], outline='black', width=2)
        draw.rectangle([x, y, x+w, y+h], fill='white', outline='gray', width=1)
        
        # Draw label above field
        draw.text((x, y-40), label, fill='black', font=font_normal)
        
        # Draw sample text in field
        draw.text((x+10, y+15), sample_text, fill='black', font=font_large)
    
    # Save with higher quality
    os.makedirs('input/samples', exist_ok=True)
    image_path = 'input/samples/high_contrast_business_form.png'
    image.save(image_path, 'PNG', quality=95, optimize=True)
    print(f"High-contrast sample form created: {image_path}")
    
    return image_path

def create_adjusted_template():
    """Create an adjusted template for the high-contrast sample"""
    template = {
        "name": "High-Contrast Business Tax Form Template",
        "description": "Adjusted template for high-contrast test form",
        "version": "1.0", 
        "fields": [
            {
                "name": "business_name",
                "x": 360,
                "y": 450, 
                "width": 900,
                "height": 75,
                "page": 1,
                "ocr_psm": 7,
                "description": "Business name field"
            },
            {
                "name": "tax_id", 
                "x": 1350,
                "y": 450,
                "width": 450,
                "height": 75,
                "page": 1,
                "ocr_psm": 8,
                "description": "Tax ID number"
            },
            {
                "name": "business_address",
                "x": 360,
                "y": 600,
                "width": 1050, 
                "height": 75,
                "page": 1,
                "ocr_psm": 7,
                "description": "Business address"
            },
            {
                "name": "city_state_zip",
                "x": 360,
                "y": 750,
                "width": 1050,
                "height": 75,
                "page": 1,
                "ocr_psm": 7,
                "description": "City, state, zip"
            },
            {
                "name": "annual_revenue", 
                "x": 1200,
                "y": 1050,
                "width": 360,
                "height": 75,
                "page": 1,
                "ocr_psm": 8,
                "description": "Annual revenue"
            },
            {
                "name": "total_expenses",
                "x": 1200,
                "y": 1200, 
                "width": 360,
                "height": 75,
                "page": 1,
                "ocr_psm": 8,
                "description": "Total expenses"
            },
            {
                "name": "net_income",
                "x": 1200,
                "y": 1350,
                "width": 360,
                "height": 75,
                "page": 1,
                "ocr_psm": 8,
                "description": "Net income"
            },
            {
                "name": "tax_year",
                "x": 1500,
                "y": 300,
                "width": 240,
                "height": 75,
                "page": 1,
                "ocr_psm": 8,
                "description": "Tax year"
            }
        ]
    }
    
    template_path = 'templates/high_contrast_business_tax.json'
    
    import json
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"Adjusted template created: {template_path}")
    return template_path

def main():
    """Test with improved sample"""
    print("🎨 Creating High-Contrast Sample Form...")
    
    # Create high-contrast sample
    sample_image = create_high_contrast_sample()
    
    # Create adjusted template
    template_path = create_adjusted_template()
    
    # Test the application
    print("\n🔄 Testing with High-Contrast Sample...")
    
    os.system(f"""
    python main.py \
        --input {sample_image} \
        --template {template_path} \
        --output output/filled_forms/high_contrast_output.pdf \
        --debug
    """)

if __name__ == "__main__":
    main()