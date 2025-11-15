"""PaddleOCR-based extractor for better Nepali/Devanagari support."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
from paddleocr import PaddleOCR
from utils.logger import get_logger
from utils.image_processing import detect_skew, correct_skew, preprocess_image

logger = get_logger(__name__)


class PaddleOCRExtractor:
    """OCR extractor using PaddleOCR for superior Nepali/Devanagari support."""
    
    def __init__(self, languages: str = "hi", use_gpu: bool = False, debug: bool = False):
        """
        Initialize PaddleOCR engine.
        
        Args:
            languages: Language code ("hi" for Hindi/Nepali, "en" for English, "hi+en" for both)
            use_gpu: Whether to use GPU acceleration
            debug: Enable debug logging
        """
        self.languages = languages
        self.use_gpu = use_gpu
        self.debug = debug
        
        try:
            # PaddleOCR initialization - API varies by version
            # Try minimal parameters first, then add optional ones
            try:
                # Newer API with use_angle_cls
                self.ocr = PaddleOCR(use_angle_cls=True, lang=languages)
            except (TypeError, ValueError):
                try:
                    # Older API - just lang
                    self.ocr = PaddleOCR(lang=languages)
                except Exception:
                    # Fallback - default initialization
                    self.ocr = PaddleOCR()
            
            logger.info(f"🔤 Initialized PaddleOCR (lang={languages})")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise
    
    def extract_from_image(self, image_path: str, save_raw: bool = True) -> Dict[str, Any]:
        """
        Extract all detected text lines from an image.
        
        Args:
            image_path: Path to input image
            save_raw: Whether to save raw OCR JSON output
            
        Returns:
            Dict with extracted text lines, confidence, and bbox
        """
        logger.info(f"🖼️ Running PaddleOCR on {image_path}")
        
        try:
            # Preprocess image (deskew, enhance)
            img = cv2.imread(image_path)
            if img is None:
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Detect and correct skew
            skew_angle = detect_skew(img)
            if abs(skew_angle) > 0.5:  # Only correct if significant skew
                logger.info(f"📐 Correcting skew: {skew_angle:.2f} degrees")
                img = correct_skew(img, skew_angle)
            
            # Preprocess for better OCR
            processed_img = preprocess_image(img)
            
            # Run PaddleOCR
            result = self.ocr.ocr(processed_img, cls=True)
            
            # Parse PaddleOCR result format
            lines = []
            if result and result[0]:
                for line in result[0]:
                    if line:
                        bbox_points = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        text_info = line[1]  # (text, confidence)
                        
                        text = text_info[0] if text_info else ""
                        confidence = text_info[1] if text_info and len(text_info) > 1 else 0.0
                        
                        if text.strip():
                            # Convert bbox to format expected by rest of system
                            x_coords = [p[0] for p in bbox_points]
                            y_coords = [p[1] for p in bbox_points]
                            x_min, x_max = int(min(x_coords)), int(max(x_coords))
                            y_min, y_max = int(min(y_coords)), int(max(y_coords))
                            
                            bbox = [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]
                            
                            lines.append({
                                "id": len(lines) + 1,
                                "text": text.strip(),
                                "confidence": round(float(confidence), 3),
                                "bbox": bbox
                            })
            
            output = {
                "image": image_path,
                "total_lines": len(lines),
                "lines": lines,
                "full_text": " ".join([l["text"] for l in lines])
            }
            
            if save_raw:
                out_path = Path(image_path).with_suffix(".paddle_ocr.json")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Saved PaddleOCR result to: {out_path}")
            
            logger.info(f"✅ Extracted {len(lines)} text lines with PaddleOCR")
            return output
            
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {e}")
            raise
    
    def extract_fields(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text for each field defined in a JSON template.
        
        Args:
            image_path: Path to input image
            template: Template dict with field definitions
            
        Returns:
            Dict mapping field_id to extracted data {name, text, confidence, bbox}
        """
        logger.info(f"📄 Extracting fields from template using PaddleOCR ({image_path})")
        
        # Get fields from template
        if "fields" in template:
            fields = template["fields"]
        elif "forms" in template and template["forms"]:
            fields = template["forms"][0]["fields"]
        else:
            raise ValueError("Invalid template format: missing 'fields' or 'forms'")
        
        # Load and preprocess image
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Scale image to match template dimensions if metadata available
        metadata = {}
        if "forms" in template and template["forms"]:
            metadata = template["forms"][0].get("metadata", {})
        elif "metadata" in template:
            metadata = template["metadata"]
        
        template_dims = metadata.get("image_dimensions_px", {})
        if template_dims:
            template_w = template_dims.get("width")
            template_h = template_dims.get("height")
            
            if template_w and template_h:
                img_h, img_w = img.shape[:2]
                if img_w != template_w or img_h != template_h:
                    logger.info(
                        f"📏 Resizing image from {img_w}x{img_h} to {template_w}x{template_h} "
                        f"to match template dimensions"
                    )
                    img = cv2.resize(img, (template_w, template_h), interpolation=cv2.INTER_LINEAR)
        
        # Detect and correct skew
        skew_angle = detect_skew(img)
        if abs(skew_angle) > 0.5:
            logger.info(f"📐 Correcting skew: {skew_angle:.2f} degrees")
            img = correct_skew(img, skew_angle)
        
        extracted = {}
        
        for field in fields:
            fid = field.get("id", "unknown")
            name = field.get("name", fid)
            bbox = field.get("bbox", {}).get("px")
            
            if not bbox or len(bbox) < 4:
                logger.warning(f"⚠️ Skipping field '{name}' — no bbox data.")
                continue
            
            x, y, w, h = map(int, bbox)
            
            # Crop field region
            region = img[y:y+h, x:x+w]
            
            if region.size == 0:
                logger.warning(f"⚠️ Skipping field '{name}' — invalid bbox dimensions.")
                continue
            
            # Preprocess region
            processed_region = preprocess_image(region)
            
            # Get OCR config from field
            ocr_config = field.get("ocr", {})
            lang = ocr_config.get("lang", self.languages)
            
            # Map template lang to PaddleOCR lang
            lang_map = {
                "nep": "hi",  # Nepali uses Hindi model
                "eng": "en",
                "nep+eng": "hi+en",
                "hi": "hi",
                "en": "en"
            }
            paddle_lang = lang_map.get(lang, "hi")
            
            try:
                # Run PaddleOCR on cropped region
                result = self.ocr.ocr(processed_region, cls=True, lang=paddle_lang)
                
                # Extract text and confidence
                text = ""
                conf = 0.0
                
                if result and result[0]:
                    texts = []
                    confidences = []
                    for line in result[0]:
                        if line and line[1]:
                            line_text = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                            line_conf = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 0.8
                            
                            if line_text:
                                texts.append(line_text.strip())
                                confidences.append(float(line_conf))
                    
                    if texts:
                        text = " ".join(texts)
                        conf = float(np.mean(confidences)) if confidences else 0.0
                
            except Exception as e:
                logger.warning(f"⚠️ PaddleOCR failed for field '{name}': {e}")
                text = ""
                conf = 0.0
            
            extracted[fid] = {
                "name": name,
                "text": text,
                "confidence": round(conf, 3),
                "bbox": {"px": bbox}
            }
            
            if self.debug:
                logger.debug(f"Field '{name}': '{text}' (conf: {conf:.2f})")
        
        logger.info(f"✅ Extracted {len(extracted)} fields using PaddleOCR")
        return extracted
    
    def extract_from_template(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compatibility method expected by CLI. Delegates to extract_fields.
        
        Args:
            image_path: Path to input image
            template: Template dict with field definitions
            
        Returns:
            Dict mapping field_id to extracted data
        """
        return self.extract_fields(image_path, template)


# Alias for backward compatibility
OCRExtractor = PaddleOCRExtractor
