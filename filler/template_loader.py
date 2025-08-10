"""
Template Loading and Validation Module

Handles loading and validation of JSON template files that define
field positions and OCR parameters for form filling.
"""

import json
import os
from typing import Dict, Any, List
from pathlib import Path


class TemplateValidationError(Exception):
    """Custom exception for template validation errors."""
    pass


class TemplateLoader:
    """Service for loading and validating JSON templates."""
    
    def __init__(self):
        """Initialize template loader."""
        pass
    
    def load_template(self, template_path: str) -> Dict[str, Any]:
        """
        Load template from JSON file.
        
        Args:
            template_path: Path to JSON template file
            
        Returns:
            Dict[str, Any]: Loaded template data
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            json.JSONDecodeError: If template file contains invalid JSON
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        return template_data
    
    def validate_template(self, template_data: Dict[str, Any]) -> None:
        """
        Validate template structure and required fields.
        
        Args:
            template_data: Template data dictionary
            
        Raises:
            TemplateValidationError: If template validation fails
        """
        # Check required root fields
        if 'fields' not in template_data:
            raise TemplateValidationError("Template must contain 'fields' array")
        
        if not isinstance(template_data['fields'], list):
            raise TemplateValidationError("Template 'fields' must be an array")
        
        if len(template_data['fields']) == 0:
            raise TemplateValidationError("Template must contain at least one field")
        
        # Validate each field
        field_names = set()
        for i, field in enumerate(template_data['fields']):
            self._validate_field(field, i, field_names)
    
    def _validate_field(self, field: Dict[str, Any], index: int, field_names: set) -> None:
        """
        Validate individual field configuration.
        
        Args:
            field: Field configuration dictionary
            index: Field index for error reporting
            field_names: Set of existing field names for uniqueness check
            
        Raises:
            TemplateValidationError: If field validation fails
        """
        # Check required fields
        required_fields = ['name', 'x', 'y', 'width', 'height']
        for req_field in required_fields:
            if req_field not in field:
                raise TemplateValidationError(
                    f"Field {index}: Missing required field '{req_field}'"
                )
        
        # Check field name uniqueness
        field_name = field['name']
        if field_name in field_names:
            raise TemplateValidationError(
                f"Field {index}: Duplicate field name '{field_name}'"
            )
        field_names.add(field_name)
        
        # Validate field name is not empty
        if not isinstance(field_name, str) or not field_name.strip():
            raise TemplateValidationError(
                f"Field {index}: Field name must be a non-empty string"
            )
        
        # Validate numeric fields
        numeric_fields = ['x', 'y', 'width', 'height']
        for num_field in numeric_fields:
            value = field[num_field]
            if not isinstance(value, (int, float)) or value < 0:
                raise TemplateValidationError(
                    f"Field {index}: '{num_field}' must be a non-negative number"
                )
        
        # Validate optional fields
        if 'page' in field:
            page = field['page']
            if not isinstance(page, int) or page < 1:
                raise TemplateValidationError(
                    f"Field {index}: 'page' must be a positive integer"
                )
        
        if 'ocr_psm' in field:
            ocr_psm = field['ocr_psm']
            if not isinstance(ocr_psm, int) or not (0 <= ocr_psm <= 13):
                raise TemplateValidationError(
                    f"Field {index}: 'ocr_psm' must be an integer between 0-13"
                )
    
    def get_fields_for_page(self, template_data: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
        """
        Get all fields for a specific page number.
        
        Args:
            template_data: Template data dictionary
            page_num: Page number to filter by
            
        Returns:
            List[Dict[str, Any]]: List of fields for the specified page
        """
        return [
            field for field in template_data['fields'] 
            if field.get('page', 1) == page_num
        ]
    
    def create_sample_template(self, output_path: str) -> None:
        """
        Create a sample template file for reference.
        
        Args:
            output_path: Path to save sample template
        """
        sample_template = {
            "name": "Business Tax Form Template",
            "description": "Template for business tax form processing",
            "version": "1.0",
            "fields": [
                {
                    "name": "business_name",
                    "x": 150,
                    "y": 700,
                    "width": 300,
                    "height": 25,
                    "page": 1,
                    "ocr_psm": 7,
                    "description": "Business name field"
                },
                {
                    "name": "tax_id",
                    "x": 150,
                    "y": 650,
                    "width": 200,
                    "height": 25,
                    "page": 1,
                    "ocr_psm": 8,
                    "description": "Tax ID number"
                },
                {
                    "name": "annual_revenue",
                    "x": 400,
                    "y": 600,
                    "width": 150,
                    "height": 25,
                    "page": 1,
                    "ocr_psm": 6,
                    "description": "Annual revenue amount"
                }
            ]
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_template, f, indent=2, ensure_ascii=False)
        
        print(f"Sample template created: {output_path}")