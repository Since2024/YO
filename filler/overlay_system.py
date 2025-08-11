"""
Overlay System Module

Handles scanning physical forms and overlaying extracted data onto pre-made
physical form templates. Supports both digital and physical form processing.
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
import time

from .scanner_integration import ScannerService


class OverlayService:
    """Service for overlaying extracted data onto physical form templates."""
    
    def __init__(self, scanner_service: Optional[ScannerService] = None):
        """
        Initialize overlay service.
        
        Args:
            scanner_service: Scanner service for physical document scanning
        """
        self.scanner_service = scanner_service or ScannerService()
        self.template_overlays = {}
        self._load_overlay_templates()
    
    def _load_overlay_templates(self) -> None:
        """Load overlay templates from templates/overlay/ directory."""
        overlay_dir = Path("templates/overlay")
        if not overlay_dir.exists():
            overlay_dir.mkdir(parents=True, exist_ok=True)
            self._create_sample_overlay_templates()
        
        for template_file in overlay_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                self.template_overlays[template_file.stem] = template_data
            except Exception as e:
                print(f"Failed to load overlay template {template_file}: {e}")
    
    def _create_sample_overlay_templates(self) -> None:
        """Create sample overlay templates."""
        sample_templates = {
            "business_tax_overlay": {
                "name": "Business Tax Form Overlay",
                "description": "Overlay template for business tax forms",
                "base_form_path": "templates/forms/business_tax_blank.pdf",
                "overlay_fields": [
                    {
                        "name": "business_name",
                        "x": 120,
                        "y": 150,
                        "width": 300,
                        "height": 25,
                        "font_size": 12,
                        "font_color": "black",
                        "alignment": "left"
                    },
                    {
                        "name": "tax_id",
                        "x": 450,
                        "y": 150,
                        "width": 150,
                        "height": 25,
                        "font_size": 12,
                        "font_color": "black",
                        "alignment": "left"
                    }
                ]
            },
            "land_tax_overlay": {
                "name": "Land Tax Form Overlay",
                "description": "Overlay template for land tax forms",
                "base_form_path": "templates/forms/land_tax_blank.pdf",
                "overlay_fields": [
                    {
                        "name": "property_owner_name",
                        "x": 100,
                        "y": 200,
                        "width": 250,
                        "height": 20,
                        "font_size": 10,
                        "font_color": "black",
                        "alignment": "left"
                    },
                    {
                        "name": "property_address",
                        "x": 100,
                        "y": 230,
                        "width": 300,
                        "height": 20,
                        "font_size": 10,
                        "font_color": "black",
                        "alignment": "left"
                    }
                ]
            }
        }
        
        for template_name, template_data in sample_templates.items():
            template_path = Path("templates/overlay") / f"{template_name}.json"
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    def scan_and_overlay(self, overlay_template: str, 
                        extracted_data: Dict[str, Dict[str, Any]],
                        output_path: Optional[str] = None) -> str:
        """
        Scan a physical form and overlay extracted data.
        
        Args:
            overlay_template: Name of overlay template to use
            extracted_data: OCR extracted data
            output_path: Path for output overlaid form (optional)
            
        Returns:
            str: Path to the overlaid form
        """
        if overlay_template not in self.template_overlays:
            raise ValueError(f"Overlay template '{overlay_template}' not found")
        
        template = self.template_overlays[overlay_template]
        
        # Scan the physical form
        print("Scanning physical form...")
        scanned_path = self.scanner_service.scan_document()
        
        # Create overlay
        return self._create_overlay(scanned_path, template, extracted_data, output_path)
    
    def overlay_on_digital_form(self, form_path: str, overlay_template: str,
                               extracted_data: Dict[str, Dict[str, Any]],
                               output_path: Optional[str] = None) -> str:
        """
        Overlay extracted data on a digital form template.
        
        Args:
            form_path: Path to digital form template
            overlay_template: Name of overlay template to use
            extracted_data: OCR extracted data
            output_path: Path for output overlaid form (optional)
            
        Returns:
            str: Path to the overlaid form
        """
        if overlay_template not in self.template_overlays:
            raise ValueError(f"Overlay template '{overlay_template}' not found")
        
        template = self.template_overlays[overlay_template]
        template['base_form_path'] = form_path
        
        return self._create_overlay(form_path, template, extracted_data, output_path)
    
    def _create_overlay(self, form_path: str, template: Dict[str, Any],
                       extracted_data: Dict[str, Dict[str, Any]],
                       output_path: Optional[str] = None) -> str:
        """
        Create overlay on form image.
        
        Args:
            form_path: Path to form image
            template: Overlay template configuration
            extracted_data: OCR extracted data
            output_path: Output path (optional)
            
        Returns:
            str: Path to overlaid form
        """
        # Generate output path if not provided
        if not output_path:
            timestamp = int(time.time())
            output_path = f"output/overlayed/overlayed_form_{timestamp}.png"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Load form image
        form_image = Image.open(form_path).convert('RGB')
        
        # Create overlay image
        overlay_image = self._create_overlay_image(form_image, template, extracted_data)
        
        # Save overlaid form
        overlay_image.save(output_path, quality=95)
        print(f"Overlaid form saved: {output_path}")
        
        return output_path
    
    def _create_overlay_image(self, form_image: Image.Image, template: Dict[str, Any],
                            extracted_data: Dict[str, Dict[str, Any]]) -> Image.Image:
        """
        Create overlay image with extracted data.
        
        Args:
            form_image: Base form image
            template: Overlay template configuration
            extracted_data: OCR extracted data
            
        Returns:
            Image.Image: Image with overlaid data
        """
        # Create a copy of the form image
        overlay_image = form_image.copy()
        draw = ImageDraw.Draw(overlay_image)
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        # Overlay each field
        for field_config in template.get('overlay_fields', []):
            field_name = field_config['name']
            
            # Get extracted text for this field
            if field_name in extracted_data:
                text = extracted_data[field_name].get('text', '')
                confidence = extracted_data[field_name].get('confidence', 0)
                
                if text and confidence > 30:  # Only overlay if confidence is reasonable
                    self._draw_overlay_text(draw, field_config, text, font)
        
        return overlay_image
    
    def _draw_overlay_text(self, draw: ImageDraw.Draw, field_config: Dict[str, Any],
                          text: str, font: ImageFont.FreeTypeFont) -> None:
        """
        Draw text overlay on form.
        
        Args:
            draw: PIL ImageDraw object
            field_config: Field configuration
            text: Text to overlay
            font: Font to use
        """
        x = field_config['x']
        y = field_config['y']
        width = field_config['width']
        height = field_config['height']
        font_size = field_config.get('font_size', 12)
        font_color = field_config.get('font_color', 'black')
        alignment = field_config.get('alignment', 'left')
        
        # Resize font if needed
        if font_size != 12:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position based on alignment
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if alignment == 'center':
            text_x = x + (width - text_width) // 2
        elif alignment == 'right':
            text_x = x + width - text_width
        else:  # left
            text_x = x
        
        # Center vertically
        text_y = y + (height - text_height) // 2
        
        # Draw text
        draw.text((text_x, text_y), text, fill=font_color, font=font)
    
    def create_overlay_template(self, template_name: str, base_form_path: str,
                              field_configurations: List[Dict[str, Any]]) -> None:
        """
        Create a new overlay template.
        
        Args:
            template_name: Name for the new template
            base_form_path: Path to base form template
            field_configurations: List of field configurations
        """
        template_data = {
            "name": template_name,
            "description": f"Overlay template for {template_name}",
            "base_form_path": base_form_path,
            "overlay_fields": field_configurations
        }
        
        # Save template
        template_path = Path("templates/overlay") / f"{template_name}.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        # Reload templates
        self._load_overlay_templates()
        print(f"Overlay template created: {template_path}")
    
    def get_available_overlay_templates(self) -> List[str]:
        """
        Get list of available overlay templates.
        
        Returns:
            List[str]: List of template names
        """
        return list(self.template_overlays.keys())
    
    def preview_overlay(self, form_path: str, overlay_template: str,
                       extracted_data: Dict[str, Dict[str, Any]]) -> str:
        """
        Create a preview of the overlay without saving.
        
        Args:
            form_path: Path to form image
            overlay_template: Name of overlay template
            extracted_data: OCR extracted data
            
        Returns:
            str: Path to preview image
        """
        if overlay_template not in self.template_overlays:
            raise ValueError(f"Overlay template '{overlay_template}' not found")
        
        template = self.template_overlays[overlay_template]
        template['base_form_path'] = form_path
        
        # Create preview path
        timestamp = int(time.time())
        preview_path = f"output/preview/overlay_preview_{timestamp}.png"
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        
        # Create overlay
        self._create_overlay(form_path, template, extracted_data, preview_path)
        
        return preview_path
    
    def batch_overlay(self, form_paths: List[str], overlay_template: str,
                     extracted_data_list: List[Dict[str, Dict[str, Any]]],
                     output_dir: Optional[str] = None) -> List[str]:
        """
        Process multiple forms with overlay.
        
        Args:
            form_paths: List of form image paths
            overlay_template: Name of overlay template
            extracted_data_list: List of extracted data for each form
            output_dir: Output directory (optional)
            
        Returns:
            List[str]: List of output paths
        """
        if len(form_paths) != len(extracted_data_list):
            raise ValueError("Number of form paths must match number of extracted data sets")
        
        if not output_dir:
            timestamp = int(time.time())
            output_dir = f"output/batch_overlay_{timestamp}"
            os.makedirs(output_dir, exist_ok=True)
        
        output_paths = []
        
        for i, (form_path, extracted_data) in enumerate(zip(form_paths, extracted_data_list)):
            output_path = f"{output_dir}/overlayed_form_{i+1:03d}.png"
            try:
                self.overlay_on_digital_form(form_path, overlay_template, extracted_data, output_path)
                output_paths.append(output_path)
            except Exception as e:
                print(f"Failed to process form {i+1}: {e}")
        
        return output_paths
    
    def validate_overlay_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate overlay template configuration.
        
        Args:
            template_name: Name of template to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        if template_name not in self.template_overlays:
            return {
                'status': 'error',
                'message': f"Template '{template_name}' not found"
            }
        
        template = self.template_overlays[template_name]
        errors = []
        
        # Check required fields
        required_fields = ['name', 'overlay_fields']
        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")
        
        # Validate overlay fields
        if 'overlay_fields' in template:
            for i, field in enumerate(template['overlay_fields']):
                field_errors = self._validate_overlay_field(field, i)
                errors.extend(field_errors)
        
        if errors:
            return {
                'status': 'error',
                'message': 'Template validation failed',
                'errors': errors
            }
        else:
            return {
                'status': 'success',
                'message': 'Template is valid'
            }
    
    def _validate_overlay_field(self, field: Dict[str, Any], index: int) -> List[str]:
        """
        Validate individual overlay field configuration.
        
        Args:
            field: Field configuration
            index: Field index
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        # Check required fields
        required_fields = ['name', 'x', 'y', 'width', 'height']
        for req_field in required_fields:
            if req_field not in field:
                errors.append(f"Field {index}: Missing required field '{req_field}'")
        
        # Validate numeric fields
        numeric_fields = ['x', 'y', 'width', 'height']
        for num_field in numeric_fields:
            if num_field in field:
                value = field[num_field]
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"Field {index}: '{num_field}' must be a non-negative number")
        
        # Validate font size
        if 'font_size' in field:
            font_size = field['font_size']
            if not isinstance(font_size, int) or font_size <= 0:
                errors.append(f"Field {index}: 'font_size' must be a positive integer")
        
        return errors
