"""OCR extraction module using PaddleOCR with preprocessing."""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from utils.logger import get_logger

logger = get_logger(__name__)


class OCRExtractor:
    """OCR extractor using PaddleOCR with multi-language support."""
    
    def __init__(self, languages: List[str] = None, use_gpu: bool = False, debug: bool = False):
        """
        Initialize OCR extractor.
        
        Args:
            languages: List of language codes (e.g., ['en', 'hi'] for English and Devanagari)
            use_gpu: Whether to use GPU acceleration
            debug: Enable debug mode
        """
        self.debug = debug
        self.languages = languages or ['en', 'hi']  # English and Devanagari (Hindi)
        
        logger.info(f"Initializing PaddleOCR with languages: {self.languages}")
        
        try:
            # Initialize PaddleOCR
            # For multi-language, we'll use 'en' as primary and handle Devanagari
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',  # Primary language
                use_gpu=use_gpu
            )
            logger.info("PaddleOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_path: Path to input image
            
        Returns:
            np.ndarray: Preprocessed image
        """
        logger.info(f"Preprocessing image: {image_path}")
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Resize if image is too small or too large
        height, width = thresh.shape
        target_height = 2000
        if height < 1000:
            scale = target_height / height
            new_width = int(width * scale)
            thresh = cv2.resize(thresh, (new_width, target_height), interpolation=cv2.INTER_CUBIC)
        elif height > 3000:
            scale = target_height / height
            new_width = int(width * scale)
            thresh = cv2.resize(thresh, (new_width, target_height), interpolation=cv2.INTER_AREA)
        
        logger.info(f"Image preprocessed. Final size: {thresh.shape}")
        return thresh
    
    def extract_from_image(self, image_path: str, save_raw: bool = True) -> Dict[str, Any]:
        """
        Extract all text from an image using OCR.
        
        Args:
            image_path: Path to input image
            save_raw: Whether to save raw OCR output as JSON
            
        Returns:
            Dict containing OCR results
        """
        logger.info(f"Starting OCR extraction on: {image_path}")
        
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Save preprocessed image if debug mode
            if self.debug:
                debug_path = f"{image_path}_preprocessed.jpg"
                cv2.imwrite(debug_path, processed_img)
                logger.debug(f"Preprocessed image saved to: {debug_path}")
            
            # Perform OCR
            result = self.ocr.ocr(processed_img, cls=True)
            
            # Parse results
            extracted_data = self._parse_ocr_result(result)
            
            # Save raw OCR output if requested
            if save_raw:
                raw_output_path = Path(image_path).with_suffix('.ocr.json')
                with open(raw_output_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Raw OCR output saved to: {raw_output_path}")
            
            logger.info(f"OCR extraction completed. Found {len(extracted_data['lines'])} text lines")
            return extracted_data
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def extract_field_from_bbox(self, image_path: str, bbox: Dict[str, List[int]]) -> Dict[str, Any]:
        """
        Extract text from a specific bounding box in the image.
        
        Args:
            image_path: Path to input image
            bbox: Bounding box with 'px' key containing [x, y, width, height]
            
        Returns:
            Dict containing extracted text and confidence
        """
        try:
            # Read and preprocess image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            # Extract bbox coordinates
            x, y, width, height = bbox['px']
            
            # Crop the region
            cropped = img[y:y+height, x:x+width]
            
            # Save cropped region if debug
            if self.debug:
                debug_path = f"{image_path}_crop_{x}_{y}.jpg"
                cv2.imwrite(debug_path, cropped)
                logger.debug(f"Cropped region saved to: {debug_path}")
            
            # Convert to grayscale and preprocess
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Perform OCR on cropped region
            result = self.ocr.ocr(thresh, cls=True)
            
            # Parse result
            if result and result[0]:
                texts = []
                confidences = []
                
                for line in result[0]:
                    if line:
                        text = line[1][0]
                        confidence = line[1][1]
                        texts.append(text)
                        confidences.append(confidence)
                
                combined_text = ' '.join(texts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                return {
                    'text': combined_text.strip(),
                    'confidence': avg_confidence,
                    'bbox': bbox
                }
            else:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'bbox': bbox
                }
                
        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bbox': bbox,
                'error': str(e)
            }
    
    def extract_from_template(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from image using a template definition.
        
        Args:
            image_path: Path to input image
            template: Template dictionary with fields definition
            
        Returns:
            Dict containing extracted data for all fields
        """
        logger.info(f"Extracting data using template: {template.get('form_type', 'unknown')}")
        
        extracted_fields = {}
        
        # Get fields from template (handle both formats)
        fields = []
        if 'forms' in template:
            # Format 1: business_tax_front.json
            fields = template['forms'][0]['fields']
        elif 'fields' in template:
            # Format 2: sampati_tax_page1_front.json
            fields = template['fields']
        
        logger.info(f"Processing {len(fields)} fields")
        
        for field in fields:
            field_id = field.get('id', field.get('name'))
            field_name = field.get('name', field_id)
            
            logger.info(f"  Extracting field: {field_name} ({field_id})")
            
            # Skip signature fields
            if field.get('type') == 'signature_box':
                logger.info(f"    Skipping signature field: {field_name}")
                extracted_fields[field_id] = {
                    'field_name': field_name,
                    'text': '[SIGNATURE]',
                    'confidence': 1.0,
                    'field_type': 'signature'
                }
                continue
            
            # Extract field
            bbox = field.get('bbox', {})
            if not bbox or 'px' not in bbox:
                logger.warning(f"    No bbox found for field: {field_name}")
                continue
            
            result = self.extract_field_from_bbox(image_path, bbox)
            
            extracted_fields[field_id] = {
                'field_name': field_name,
                'text': result['text'],
                'confidence': result['confidence'],
                'field_type': field.get('type', 'text'),
                'label': field.get('label', field_name)
            }
            
            if self.debug:
                logger.debug(f"    Text: '{result['text']}' (confidence: {result['confidence']:.2f})")
        
        logger.info(f"Extraction completed. {len(extracted_fields)} fields extracted")
        return extracted_fields
    
    def _parse_ocr_result(self, result: List) -> Dict[str, Any]:
        """
        Parse PaddleOCR result into structured format.
        
        Args:
            result: Raw PaddleOCR result
            
        Returns:
            Dict containing parsed OCR data
        """
        lines = []
        
        if result and result[0]:
            for idx, line in enumerate(result[0]):
                if line:
                    bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    lines.append({
                        'line_number': idx + 1,
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })
        
        return {
            'total_lines': len(lines),
            'lines': lines,
            'full_text': ' '.join([line['text'] for line in lines])
        }
