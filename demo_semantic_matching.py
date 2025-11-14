#!/usr/bin/env python3
"""
Quick demo script for semantic field matching.
Run this to test semantic matching without the web UI.
"""

import json
from pathlib import Path
from filler.form_filler import FormFiller
from ocr.extractor import OCRExtractor

def demo_semantic_matching():
    """Demonstrate semantic field matching."""
    
    print("=" * 60)
    print("🧠 Semantic Field Matching Demo")
    print("=" * 60)
    print()
    
    # Initialize components
    form_filler = FormFiller()
    extractor = OCRExtractor(languages="nep+eng", debug=False)
    
    # Load template
    template_path = "templates/sampati_tax_page1_front.json"
    print(f"📄 Loading template: {template_path}")
    template = form_filler.load_template(template_path)
    
    # Get template fields
    if 'fields' in template:
        template_fields = template['fields']
    elif 'forms' in template and template['forms']:
        template_fields = template['forms'][0]['fields']
    else:
        print("❌ Invalid template format")
        return
    
    print(f"✅ Template loaded: {len(template_fields)} fields")
    print()
    
    # Try to find a sample image
    sample_images = [
        "input/sample/id.jpg",
        "templates/business_front.jpg",
        "templates/sampati_front.jpg"
    ]
    
    image_path = None
    for img in sample_images:
        if Path(img).exists():
            image_path = img
            break
    
    if not image_path:
        print("⚠️  No sample image found. Please provide an image path.")
        print("   Usage: python demo_semantic_matching.py <image_path>")
        return
    
    print(f"🖼️  Processing image: {image_path}")
    print()
    
    # Extract full OCR
    print("🔍 Running OCR on full image...")
    ocr_result = extractor.extract_from_image(image_path, save_raw=False)
    
    print(f"✅ Extracted {ocr_result['total_lines']} text lines")
    print()
    print("📝 Sample OCR lines:")
    for i, line in enumerate(ocr_result['lines'][:5], 1):
        print(f"   {i}. {line['text']} (confidence: {line['confidence']:.2f})")
    if len(ocr_result['lines']) > 5:
        print(f"   ... and {len(ocr_result['lines']) - 5} more lines")
    print()
    
    # Match semantically
    print("🧠 Matching OCR text to template fields semantically...")
    print()
    
    matched_data = form_filler.match_ocr_to_template_semantically(
        ocr_result,
        template,
        save_mapping="output/demo/semantic_mapping.json"
    )
    
    # Display results
    print("=" * 60)
    print("📊 Matching Results")
    print("=" * 60)
    print()
    
    matched_count = 0
    for field_id, data in matched_data.items():
        if data.get('text'):
            matched_count += 1
            match_score = data.get('match_score', 0.0)
            matched_from = data.get('matched_from', 'N/A')
            
            print(f"✅ {data['name']}")
            print(f"   Value: {data['text']}")
            print(f"   Match Score: {match_score:.2f}")
            print(f"   Matched from OCR: '{matched_from}'")
            print(f"   Confidence: {data['confidence']:.2f}")
            print()
    
    unmatched_count = len(matched_data) - matched_count
    if unmatched_count > 0:
        print(f"⚠️  {unmatched_count} fields not matched")
        print()
    
    print(f"📈 Summary: {matched_count}/{len(matched_data)} fields matched")
    print()
    print(f"💾 Full mapping saved to: output/demo/semantic_mapping.json")
    print()
    print("=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Override image path if provided
        image_path = sys.argv[1]
        if not Path(image_path).exists():
            print(f"❌ Image not found: {image_path}")
            sys.exit(1)
        # Modify the function to use provided image
        def demo_with_image():
            form_filler = FormFiller()
            extractor = OCRExtractor(languages="nep+eng", debug=False)
            template = form_filler.load_template("templates/sampati_tax_page1_front.json")
            
            if 'fields' in template:
                template_fields = template['fields']
            elif 'forms' in template and template['forms']:
                template_fields = template['forms'][0]['fields']
            else:
                print("❌ Invalid template format")
                return
            
            print(f"🖼️  Processing image: {image_path}")
            ocr_result = extractor.extract_from_image(image_path, save_raw=False)
            matched_data = form_filler.match_ocr_to_template_semantically(
                ocr_result, template, save_mapping="output/demo/semantic_mapping.json"
            )
            
            print("\n✅ Matching Results:")
            for field_id, data in matched_data.items():
                if data.get('text'):
                    print(f"  {data['name']}: {data['text']} (score: {data.get('match_score', 0):.2f})")
        
        demo_with_image()
    else:
        demo_semantic_matching()

