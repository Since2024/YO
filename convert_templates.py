#!/usr/bin/env python3
"""
Template Format Converter

Converts the real-world templates from the GitHub repository to 
FirstChild compatible format.
"""

import json
import os
from pathlib import Path


def convert_real_template_to_firstchild(input_file: str, output_file: str, page_num: int = 1):
    """
    Convert real template format to FirstChild format.
    
    Args:
        input_file: Path to input real template file
        output_file: Path to output FirstChild template file  
        page_num: Page number for multi-page templates
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        real_template = json.load(f)
    
    # Extract basic info
    if 'forms' in real_template and len(real_template['forms']) > 0:
        form_data = real_template['forms'][0]
        fields_data = form_data.get('fields', [])
        form_type = form_data.get('form_type', 'Unknown Form')
    else:
        fields_data = real_template.get('fields', [])
        form_type = real_template.get('form_type', 'Unknown Form')
    
    # Convert to FirstChild format
    firstchild_template = {
        "name": form_type,
        "description": f"Real-world template for {form_type}",
        "version": "1.0",
        "source": "GitHub repository - Since2024/FirstChild",
        "fields": []
    }
    
    # Convert each field
    for field in fields_data:
        field_name = field.get('field_name', 'unnamed_field')
        
        # Skip signature boxes and section headers for now
        if field.get('field_type') in ['signature_box', 'section_header', 'checkbox_section']:
            continue
            
        # Extract coordinates from pixel_bbox
        pixel_bbox = field.get('pixel_bbox', {})
        
        firstchild_field = {
            "name": field_name,
            "x": pixel_bbox.get('x', 0),
            "y": pixel_bbox.get('y', 0),
            "width": pixel_bbox.get('width', 100),
            "height": pixel_bbox.get('height', 25),
            "page": page_num,
            "ocr_psm": get_optimal_psm_for_field(field),
            "description": f"{field_name} field",
            "field_type": field.get('field_type', 'text_line'),
            "confidence": field.get('confidence', 0.9)
        }
        
        firstchild_template["fields"].append(firstchild_field)
    
    # Save converted template
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(firstchild_template, f, indent=2, ensure_ascii=False)
    
    print(f"Converted {input_file} -> {output_file}")
    print(f"  Fields converted: {len(firstchild_template['fields'])}")


def get_optimal_psm_for_field(field):
    """Get optimal OCR PSM mode based on field type"""
    field_type = field.get('field_type', 'text_line')
    
    psm_map = {
        'text_line': 7,      # Single text line
        'box_grid': 8,       # Single word/number
        'text_block': 6,     # Uniform block of text
        'signature_box': 13, # Raw line. Treat as single character
        'section_header': 7  # Single text line
    }
    
    return psm_map.get(field_type, 7)


def main():
    """Convert all real templates to FirstChild format"""
    
    print("🔄 Converting Real Templates to FirstChild Format")
    print("=" * 50)
    
    conversions = [
        {
            "input": "templates/business_tax_page1_real.json",
            "output": "templates/business_tax_page1_converted.json", 
            "page": 1
        },
        {
            "input": "templates/business_tax_page2_real.json",
            "output": "templates/business_tax_page2_converted.json",
            "page": 2  
        },
        {
            "input": "templates/land_tax_front_real.json", 
            "output": "templates/land_tax_front_converted.json",
            "page": 1
        },
        {
            "input": "templates/land_tax_table_back_real.json",
            "output": "templates/land_tax_back_converted.json",
            "page": 2
        }
    ]
    
    for conversion in conversions:
        try:
            convert_real_template_to_firstchild(
                conversion["input"],
                conversion["output"], 
                conversion["page"]
            )
        except Exception as e:
            print(f"❌ Failed to convert {conversion['input']}: {e}")
    
    print("\n✅ Template conversion completed!")
    
    # List all available templates
    print("\n📋 Available Templates:")
    template_files = list(Path("templates").glob("*.json"))
    for template_file in sorted(template_files):
        file_size = template_file.stat().st_size
        print(f"  • {template_file.name} ({file_size} bytes)")


if __name__ == "__main__":
    main()