"""Form filling logic for mapping OCR data to form fields."""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from utils.logger import get_logger
from .field_matcher import FieldMatcher
from .validators import FieldValidator

logger = get_logger(__name__)


class FormFiller:
    """Handles form filling operations and data mapping."""
    
    def __init__(self, field_matcher: Optional[FieldMatcher] = None):
        """
        Initialize form filler.
        
        Args:
            field_matcher: Optional FieldMatcher instance for semantic matching.
                          If None, creates a default one.
        """
        self.field_matcher = field_matcher or FieldMatcher(confidence_threshold=0.7, debug=False)
        logger.info("FormFiller initialized with semantic field matching capability")
    
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
                               template: Dict[str, Any],
                               confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Validate extracted data against template validation rules.
        
        Args:
            extracted_data: Extracted OCR data
            template: Form template with validation rules
            confidence_threshold: Minimum confidence threshold for auto-approval (default 0.7)
            
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
                # Mark for review if required
                if field.get('validate', {}).get('req', False):
                    extracted_data[field_id] = {
                        'name': field_name,
                        'text': '',
                        'confidence': 0.0,
                        'bbox': field.get('bbox', {}),
                        'needs_review': True
                    }
                continue
            
            field_data = extracted_data[field_id]
            text = field_data.get('text', '')
            confidence = field_data.get('confidence', 0.0)
            
            # Check validation rules
            validation = field.get('validate', {})
            
            # Determine if field needs review
            needs_review = False
            
            # Required field check
            if validation.get('req', False) and not text:
                validation_results['valid'] = False
                validation_results['errors'].append(
                    f"Required field '{field_name}' is empty"
                )
                needs_review = True
            
            # Low confidence flag
            if confidence < confidence_threshold:
                if text:
                    validation_results['warnings'].append(
                        f"Field '{field_name}' has low confidence: {confidence:.2f}"
                    )
                needs_review = True
            
            # Length validation
            if 'len' in validation and text:
                expected_len = validation['len']
                actual_len = len(text.replace(' ', ''))
                if actual_len != expected_len:
                    validation_results['warnings'].append(
                        f"Field '{field_name}' length mismatch. Expected {expected_len}, got {actual_len}"
                    )
                    needs_review = True
            
            # Format validation using FieldValidator
            field_type = validation.get('type', field.get('type', 'string'))
            if field_type in ['date', 'phone', 'mobile', 'citizenship', 'pan', 'email', 'number', 'numeric']:
                # Create a copy for validation
                field_copy = field_data.copy()
                field_copy['validate'] = validation
                validated = FieldValidator.validate_field(field_copy, field_type)
                
                if not validated.get('valid', True):
                    validation_results['warnings'].append(
                        f"Field '{field_name}' format validation failed (type: {field_type})"
                    )
                    needs_review = True
                elif validated.get('normalized') and validated['normalized'] != text:
                    # Update with normalized value
                    extracted_data[field_id]['text'] = validated['normalized']
                    logger.debug(f"Normalized field '{field_name}': '{text}' → '{validated['normalized']}'")
            
            # Set needs_review flag
            extracted_data[field_id]['needs_review'] = needs_review
        
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
        Prepare extracted data for PDF generation with support for table rows and box_grid.
        
        Args:
            extracted_data: Extracted OCR data
            template: Form template
            
        Returns:
            List of field data ready for PDF generation with rendering metadata
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
                    'type': field.get('type', 'text_line'),
                    'page': field.get('page', 1),
                    'confidence': field_data.get('confidence', 0.0),
                    'needs_review': field_data.get('needs_review', False)
                }
                
                # Add box_grid metadata if present
                if field.get('type') == 'box_grid' and 'grid' in field:
                    pdf_field['grid'] = field['grid']
                    pdf_field['rendering'] = 'box_grid'
                
                # Add table metadata if present
                elif field.get('type') == 'table' and 'table' in field:
                    pdf_field['table'] = field['table']
                    pdf_field['rendering'] = 'table'
                    # Support for table rows
                    if 'rows' in field_data:
                        pdf_field['rows'] = field_data['rows']
                
                # Add rendering metadata for other types
                else:
                    pdf_field['rendering'] = 'text'
                
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
    
    def match_ocr_to_template_semantically(
        self,
        ocr_result: Dict[str, Any],
        template: Dict[str, Any],
        save_mapping: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Use semantic field matching to map OCR text to template fields.
        
        This method is useful when:
        - Extracting from ID cards or documents without predefined bbox regions
        - OCR extracts text like "नाम : हसन गाहा" that needs to map to template fields
        
        Args:
            ocr_result: Full OCR result from extract_from_image() with 'lines' key
            template: Template dict with field definitions
            save_mapping: Optional path to save the matched mapping JSON
            
        Returns:
            Dict mapping field_id to matched data {name, text, confidence, bbox, match_score}
        """
        logger.info("Starting semantic field matching process")
        
        matched_data = self.field_matcher.match_from_full_ocr(ocr_result, template)
        
        # Save mapping if requested
        if save_mapping:
            try:
                Path(save_mapping).parent.mkdir(parents=True, exist_ok=True)
                with open(save_mapping, 'w', encoding='utf-8') as f:
                    json.dump(matched_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved semantic mapping to: {save_mapping}")
            except Exception as e:
                logger.warning(f"Failed to save mapping: {e}")
        
        return matched_data
    
    def extract_and_match_semantically(
        self,
        image_path: str,
        template: Dict[str, Any],
        ocr_extractor: Any,
        save_mapping: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract OCR from image and semantically match to template fields.
        
        This is a convenience method that combines OCR extraction with semantic matching.
        Useful for processing ID cards or documents where bbox-based extraction isn't suitable.
        
        Args:
            image_path: Path to input image
            template: Template dict with field definitions
            ocr_extractor: OCRExtractor instance
            save_mapping: Optional path to save the matched mapping JSON
            
        Returns:
            Dict mapping field_id to matched data
        """
        logger.info(f"Extracting OCR from image and matching semantically: {image_path}")
        
        # Extract full OCR from image
        ocr_result = ocr_extractor.extract_from_image(image_path, save_raw=False)
        
        # Match semantically
        matched_data = self.match_ocr_to_template_semantically(
            ocr_result,
            template,
            save_mapping=save_mapping
        )
        
        return matched_data
