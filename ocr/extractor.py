"""OCR extraction module using Tesseract OCR (pytesseract)."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
import pytesseract  # type: ignore
from PIL import Image
from utils.logger import get_logger

logger = get_logger(__name__)

# Ensure Tesseract can locate language data shipped with the project (if available)
DEFAULT_TESSDATA_DIR = Path(__file__).resolve().parents[1] / "tessdata"
if DEFAULT_TESSDATA_DIR.exists() and "TESSDATA_PREFIX" not in os.environ:
    os.environ["TESSDATA_PREFIX"] = str(DEFAULT_TESSDATA_DIR)
    logger.info(f"Using bundled tessdata directory: {DEFAULT_TESSDATA_DIR}")


class TesseractExtractor:
    """OCR extractor for multi-language Nepali forms using Tesseract OCR."""

    def __init__(self, languages: str = "nep+eng", debug: bool = False):
        """
        Initialize Tesseract OCR engine.
        
        Args:
            languages: Language codes for Tesseract (e.g., "nep+eng", "eng", "nep")
            debug: Save intermediate files for inspection
        """
        self.languages = languages
        self.debug = debug
        
        # Verify Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info(f"🔤 Initializing Tesseract OCR (lang={languages})")
        except Exception as e:
            logger.error(f"Tesseract OCR not found: {e}")
            logger.error("Please install Tesseract: sudo pacman -S tesseract tesseract-data-nep")
            raise

    # ----------------------------------------------------
    # 🧩 Step 1: Image Preprocessing
    # ----------------------------------------------------
    def preprocess(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for OCR: grayscale, denoise, adaptive threshold.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Preprocessed image as numpy array
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10
        )

        if self.debug:
            debug_path = Path(image_path).with_name("debug_preprocessed.jpg")
            cv2.imwrite(str(debug_path), thresh)
            logger.debug(f"Saved preprocessed image: {debug_path}")

        return thresh

    # ----------------------------------------------------
    # 🧠 Step 2: Full Image OCR
    # ----------------------------------------------------
    def extract_from_image(self, image_path: str, save_raw: bool = True) -> Dict[str, Any]:
        """
        Extract all detected text lines from an image.
        
        Args:
            image_path: Path to input image
            save_raw: Whether to save raw OCR JSON output
            
        Returns:
            Dict with extracted text lines, confidence, and bbox
        """
        logger.info(f"🖼️ Running OCR on {image_path}")

        # Preprocess image
        img = self.preprocess(image_path)
        
        # Convert to PIL Image for pytesseract
        pil_image = Image.fromarray(img)
        
        # Run OCR with detailed output
        ocr_data = pytesseract.image_to_data(
            pil_image,
            lang=self.languages,
            output_type=pytesseract.Output.DICT,
            config='--psm 6'
        )
        
        # Parse OCR results
        lines = []
        current_line = None
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = float(ocr_data['conf'][i]) if ocr_data['conf'][i] != -1 else 0.0
            
            if text:  # Only process non-empty text
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                
                lines.append({
                    "id": len(lines) + 1,
                    "text": text,
                    "confidence": round(conf / 100.0, 3),  # Normalize to 0-1
                    "bbox": bbox
                })

        output = {
            "image": image_path,
            "total_lines": len(lines),
            "lines": lines,
            "full_text": " ".join([l["text"] for l in lines])
        }

        if save_raw:
            out_path = Path(image_path).with_suffix(".ocr.json")
            # Ensure output directory exists
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Saved OCR result to: {out_path}")

        logger.info(f"✅ Extracted {len(lines)} text lines")
        return output

    # ----------------------------------------------------
    # 🧩 Step 3: Field-wise OCR (for template-based extraction)
    # ----------------------------------------------------
    def extract_fields(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text for each field defined in a JSON template.
        
        Args:
            image_path: Path to input image
            template: Template dict with field definitions
            
        Returns:
            Dict mapping field_id to extracted data {name, text, confidence, bbox}
        """
        logger.info(f"📄 Extracting fields from template ({image_path})")

        # Get fields from template
        if "fields" in template:
            fields = template["fields"]
        elif "forms" in template and template["forms"]:
            fields = template["forms"][0]["fields"]
        else:
            raise ValueError("Invalid template format: missing 'fields' or 'forms'")

        # Load full image
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

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
            gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            denoised_region = cv2.fastNlMeansDenoising(gray_region, None, 10, 7, 21)
            
            # Get OCR config from field if available
            ocr_config = field.get("ocr", {})
            psm = ocr_config.get("psm", 7)  # Default PSM 7 for single text line
            lang = ocr_config.get("lang", self.languages)
            
            # Convert to PIL Image
            pil_region = Image.fromarray(denoised_region)
            
            # Run OCR on cropped field
            try:
                ocr_result = pytesseract.image_to_string(
                    pil_region,
                    lang=lang,
                    config=f'--psm {psm}'
                )
                text = ocr_result.strip()
                
                # Get confidence score
                ocr_data = pytesseract.image_to_data(
                    pil_region,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                    config=f'--psm {psm}'
                )
                
                # Calculate average confidence
                confidences = [float(c) for c in ocr_data['conf'] if c != -1]
                conf = float(np.mean(confidences) / 100.0) if confidences else 0.0
                
            except Exception as e:
                logger.warning(f"⚠️ OCR failed for field '{name}': {e}")
                text = ""
                conf = 0.0

            extracted[fid] = {
                "name": name,
                "text": text,
                "confidence": round(conf, 3),
                "bbox": {"px": bbox}
            }

            logger.debug(f"Field '{name}': '{text}' (conf: {conf:.2f})")

        logger.info(f"✅ Extracted {len(extracted)} fields from template")
        return extracted

    # ----------------------------------------------------
    # 🔗 Compatibility wrapper for main CLI
    # ----------------------------------------------------
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
OCRExtractor = TesseractExtractor


if __name__ == "__main__":
    """Test hook for direct module execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test OCR extractor")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--template", help="Path to template JSON (optional)")
    parser.add_argument("--lang", default="nep+eng", help="OCR languages")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    extractor = TesseractExtractor(languages=args.lang, debug=args.debug)
    
    if args.template:
        import json
        with open(args.template, 'r', encoding='utf-8') as f:
            template = json.load(f)
        result = extractor.extract_from_template(args.image, template)
        print(f"\n✅ Extracted {len(result)} fields:")
        for fid, data in result.items():
            print(f"  {data['name']}: '{data['text']}' (conf: {data['confidence']:.2f})")
    else:
        result = extractor.extract_from_image(args.image)
        print(f"\n✅ Extracted {result['total_lines']} text lines")
        print(f"Full text: {result['full_text'][:200]}...")
