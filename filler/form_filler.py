"""Form filling logic for mapping OCR data to form fields."""

import json
from typing import Dict, Any, List
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class FormFiller:
    """Handles form filling operations and data mapping."""
    
    def __init__(self):
        """Initialize form filler."""
        pass
    
    def load_template(self, template_path: str) -> Dict[str, Any]:
        """
        Load form template from JSON file.
        
        Args:
            template_path: Path to template JSON file
            
        Returns:
            Dict containing template data
        """
        logger.info(f"Loading template: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            logger.info(f"Template loaded successfully")
            return template
            
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            raise
    
    def validate_extracted_data(self, extracted_data: Dict[str, Any], 
                               template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data against template validation rules.
        
        Args:
            extracted_data: Extracted OCR data
            template: Form template with validation rules
            
        Returns:
            Dict containing validation results
        """
        logger.info("Validating extracted data")
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Get fields from template
        fields = []
        if 'forms' in template:
            fields = template['forms'][0]['fields']
        elif 'fields' in template:
            fields = template['fields']
        
        for field in fields:
            field_id = field.get('id', field.get('name'))
            field_name = field.get('name', field_id)
            
            # Check if field exists in extracted data
            if field_id not in extracted_data:
                validation_results['warnings'].append(
                    f"Field '{field_name}' not found in extracted data"
                )
                continue
            
            field_data = extracted_data[field_id]
            text = field_data.get('text', '')
            confidence = field_data.get('confidence', 0.0)
            
            # Check validation rules
            validation = field.get('validate', {})
            
            # Required field check
            if validation.get('req', False) and not text:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Required field '{field_name}' is empty"
                )
            
            # Low confidence warning
            if confidence < 0.7 and text:
                validation_results['warnings'].append(
                    f"Field '{field_name}' has low confidence: {confidence:.2f}"
                )
            
            # Length validation
            if 'len' in validation and text:
                expected_len = validation['len']
                actual_len = len(text.replace(' ', ''))
                if actual_len != expected_len:
                    validation_results['warnings'].append(
                        f"Field '{field_name}' length mismatch. Expected {expected_len}, got {actual_len}"
                    )
        
        if validation_results['valid']:
            logger.info("Validation passed")
        else:
            logger.warning(f"Validation failed with {len(validation_results['errors'])} errors")
        
        if validation_results['warnings']:
            logger.warning(f"{len(validation_results['warnings'])} validation warnings")
        
        return validation_results
    
    def prepare_data_for_pdf(self, extracted_data: Dict[str, Any], 
                            template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prepare extracted data for PDF generation.
        
        Args:
            extracted_data: Extracted OCR data
            template: Form template
            
        Returns:
            List of field data ready for PDF generation
        """
        logger.info("Preparing data for PDF generation")
        
        pdf_data = []
        
        # Get fields from template
        fields = []
        if 'forms' in template:
            fields = template['forms'][0]['fields']
        elif 'fields' in template:
            fields = template['fields']
        
        for field in fields:
            field_id = field.get('id', field.get('name'))
            
            if field_id in extracted_data:
                field_data = extracted_data[field_id]
                
                pdf_field = {
                    'id': field_id,
                    'name': field.get('name', field_id),
                    'text': field_data.get('text', ''),
                    'bbox': field.get('bbox', {}),
                    'type': field.get('type', 'text'),
                    'page': field.get('page', 1),
                    'confidence': field_data.get('confidence', 0.0)
                }
                
                pdf_data.append(pdf_field)
        
        logger.info(f"Prepared {len(pdf_data)} fields for PDF generation")
        return pdf_data
    
    def save_extracted_json(self, extracted_data: Dict[str, Any], 
                           output_path: str) -> None:
        """
        Save extracted data as JSON file.
        
        Args:
            extracted_data: Extracted data to save
            output_path: Path for output JSON file
        """
        logger.info(f"Saving extracted data to: {output_path}")
        
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Extracted data saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save extracted data: {e}")
            raise
