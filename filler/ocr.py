"""
OCR Extraction Module

Handles OCR processing using pytesseract with configurable PSM modes
and confidence scoring for extracted text data.
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from PIL import Image
import pytesseract
from pathlib import Path


class OCRExtractor:
    """Service for extracting text from images using OCR."""
    
    # Default OCR configuration
    DEFAULT_CONFIG = r'--oem 3 --psm 6'
    
    def __init__(self, language: str = 'eng', debug: bool = False):
        """
        Initialize OCR extractor.
        
        Args:
            language: OCR language code (default: eng)
            debug: Enable debug mode for saving intermediate images
        """
        self.language = language
        self.debug = debug
        
        # Verify pytesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise RuntimeError(f"Tesseract not found or not properly installed: {e}")
    
    def extract_from_page(self, image: Image.Image, template_data: Dict[str, Any], 
                         page_num: int) -> Dict[str, Dict[str, Any]]:
        """
        Extract text from all fields on a specific page.
        
        Args:
            image: PIL Image of the page
            template_data: Template configuration
            page_num: Page number to process
            
        Returns:
            Dict[str, Dict[str, Any]]: Extracted data with field names as keys
        """
        extracted_data = {}
        page_fields = [
            field for field in template_data['fields']
            if field.get('page', 1) == page_num
        ]
        
        print(f"Processing {len(page_fields)} fields on page {page_num}...")
        
        for field in page_fields:
            field_name = field['name']
            print(f"  Extracting field: {field_name}")
            
            # Extract text from field region
            result = self._extract_field_text(image, field)
            extracted_data[field_name] = result
            
            if self.debug:
                print(f"    Text: '{result['text']}' (confidence: {result['confidence']:.2f}%)")
        
        return extracted_data
    
    def _extract_field_text(self, image: Image.Image, field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from a specific field region.
        
        Args:
            image: PIL Image of the page
            field: Field configuration
            
        Returns:
            Dict[str, Any]: Extraction result with text, confidence, and metadata
        """
        # Get field coordinates and dimensions
        x = int(field['x'])
        y = int(field['y'])
        width = int(field['width'])
        height = int(field['height'])
        
        # Convert PIL coordinate system (top-left origin) to crop region
        # PIL uses (left, top, right, bottom) format
        crop_box = (x, y, x + width, y + height)
        
        # Crop the field region
        field_image = image.crop(crop_box)
        
        # Save debug image if enabled
        if self.debug:
            debug_path = f"output/debug_{field['name']}_crop.png"
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            field_image.save(debug_path)
        
        # Configure OCR parameters
        ocr_config = self._get_ocr_config(field)
        
        try:
            # Extract text with confidence scores
            data = pytesseract.image_to_data(
                field_image, 
                lang=self.language, 
                config=ocr_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Process OCR results
            text, confidence = self._process_ocr_data(data)
            
            return {
                'text': text.strip(),
                'confidence': confidence,
                'field_name': field['name'],
                'coordinates': {
                    'x': x, 'y': y, 'width': width, 'height': height
                },
                'ocr_config': ocr_config
            }
            
        except Exception as e:
            print(f"    Warning: OCR failed for field {field['name']}: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'field_name': field['name'],
                'coordinates': {
                    'x': x, 'y': y, 'width': width, 'height': height
                },
                'error': str(e)
            }
    
    def _get_ocr_config(self, field: Dict[str, Any]) -> str:
        """
        Get OCR configuration for a specific field.
        
        Args:
            field: Field configuration
            
        Returns:
            str: OCR configuration string
        """
        # Use field-specific PSM if provided, otherwise use default
        psm = field.get('ocr_psm', 6)
        return f'--oem 3 --psm {psm}'
    
    def _process_ocr_data(self, ocr_data: Dict[str, Any]) -> Tuple[str, float]:
        """
        Process OCR data to extract text and calculate average confidence.
        
        Args:
            ocr_data: OCR data dictionary from pytesseract
            
        Returns:
            Tuple[str, float]: Extracted text and average confidence
        """
        texts = []
        confidences = []
        
        for i, conf in enumerate(ocr_data['conf']):
            if int(conf) > 0:  # Only include confident detections
                text = ocr_data['text'][i].strip()
                if text:  # Only include non-empty text
                    texts.append(text)
                    confidences.append(float(conf))
        
        # Combine text and calculate average confidence
        combined_text = ' '.join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return combined_text, avg_confidence
    
    def preprocess_field_image(self, image: Image.Image) -> Image.Image:
        """
        Apply additional preprocessing to field image for better OCR.
        
        Args:
            image: Field image to preprocess
            
        Returns:
            Image.Image: Preprocessed image
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale if not already
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # Apply slight dilation to make text thicker
        processed = cv2.dilate(processed, kernel, iterations=1)
        
        # Convert back to PIL Image
        return Image.fromarray(processed)
    
    def get_ocr_languages(self) -> list:
        """
        Get list of available OCR languages.
        
        Returns:
            list: List of available language codes
        """
        try:
            return pytesseract.get_languages(config='')
        except:
            return ['eng']  # Return default if unable to get languages
    
    def test_ocr_installation(self) -> Dict[str, Any]:
        """
        Test OCR installation and return system information.
        
        Returns:
            Dict[str, Any]: System information and test results
        """
        try:
            version = pytesseract.get_tesseract_version()
            languages = self.get_ocr_languages()
            
            # Test OCR with a simple image
            test_image = Image.new('RGB', (200, 50), color='white')
            test_result = pytesseract.image_to_string(test_image)
            
            return {
                'status': 'success',
                'version': str(version),
                'available_languages': languages,
                'test_successful': True
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'test_successful': False
            }