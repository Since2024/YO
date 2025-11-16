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
                else:
                    logger.debug(f"✅ Image dimensions match template: {img_w}x{img_h}")

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

            # Enhanced preprocessing for field regions
            gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for better contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray_region)
            
            # Denoise
            denoised_region = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # Get OCR config from field if available
            ocr_config = field.get("ocr", {})
            psm = ocr_config.get("psm", 7)  # Default PSM 7 for single text line
            lang = ocr_config.get("lang", self.languages)
            whitelist = ocr_config.get("whitelist")
            
            # Try multiple preprocessing strategies
            preprocessed_regions = []
            
            # Strategy 1: Otsu threshold (usually best for varying contrast)
            _, thresh_otsu = cv2.threshold(denoised_region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_regions.append(("otsu", thresh_otsu))
            
            # Strategy 2: Adaptive threshold (for high contrast)
            thresh_adaptive = cv2.adaptiveThreshold(
                denoised_region, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
            )
            preprocessed_regions.append(("adaptive", thresh_adaptive))
            
            # Strategy 3: Original denoised (for light backgrounds)
            preprocessed_regions.append(("denoised", denoised_region))
            
            # Try OCR with multiple strategies
            text = ""
            conf = 0.0
            best_strategy = None
            
            # Build OCR strategies to try
            ocr_strategies = [
                {"psm": psm, "lang": lang, "whitelist": whitelist},
            ]
            
            # Add alternative PSM if different
            if psm != 8:
                ocr_strategies.append({"psm": 8, "lang": lang, "whitelist": whitelist})
            if psm != 7:
                ocr_strategies.append({"psm": 7, "lang": lang, "whitelist": whitelist})
            
            # Try both languages if only one specified
            if lang != "nep+eng":
                ocr_strategies.append({"psm": psm, "lang": "nep+eng", "whitelist": whitelist})
            
            # Try each preprocessing strategy with each OCR strategy
            for prep_name, preprocessed_region in preprocessed_regions:
                pil_region = Image.fromarray(preprocessed_region)
                
                for strategy in ocr_strategies:
                    try:
                        # Build config string
                        config_parts = [f"--psm {strategy['psm']}", "--oem 3"]
                        if strategy.get("whitelist"):
                            config_parts.append(f"-c tessedit_char_whitelist={strategy['whitelist']}")
                        config_str = " ".join(config_parts)
                        
                        ocr_result = pytesseract.image_to_string(
                            pil_region,
                            lang=strategy["lang"],
                            config=config_str
                        )
                        test_text = ocr_result.strip()
                        
                        if test_text:
                            # Get confidence for this strategy
                            ocr_data = pytesseract.image_to_data(
                                pil_region,
                                lang=strategy["lang"],
                                output_type=pytesseract.Output.DICT,
                                config=config_str
                            )
                            confidences = [float(c) for c in ocr_data['conf'] if c != -1]
                            test_conf = float(np.mean(confidences) / 100.0) if confidences else 0.0
                            
                            # Use this result if it's better (longer text or higher confidence)
                            if len(test_text) > len(text) or (len(test_text) == len(text) and test_conf > conf):
                                text = test_text
                                conf = test_conf
                                best_strategy = f"{prep_name}+psm{strategy['psm']}+{strategy['lang']}"
                    except Exception as e:
                        if self.debug:
                            logger.debug(f"Strategy {prep_name}+psm{strategy['psm']} failed: {e}")
                        continue
            
            # Last resort: try with original gray region (no preprocessing)
            if not text:
                try:
                    pil_region = Image.fromarray(gray_region)
                    config_str = f"--psm {psm} --oem 3"
                    if whitelist:
                        config_str += f" -c tessedit_char_whitelist={whitelist}"
                    
                    ocr_result = pytesseract.image_to_string(
                        pil_region,
                        lang=lang,
                        config=config_str
                    )
                    text = ocr_result.strip()
                    
                    if text:
                        ocr_data = pytesseract.image_to_data(
                            pil_region,
                            lang=lang,
                            output_type=pytesseract.Output.DICT,
                            config=config_str
                        )
                        confidences = [float(c) for c in ocr_data['conf'] if c != -1]
                        conf = float(np.mean(confidences) / 100.0) if confidences else 0.0
                        best_strategy = "original_gray"
                except Exception as e:
                    logger.debug(f"Last resort OCR failed for field '{name}': {e}")
            
            if self.debug and best_strategy:
                logger.debug(f"Field '{name}' best strategy: {best_strategy}")
            
            if not text:
                logger.warning(f"⚠️ No text extracted for field '{name}'")

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


class OCRExtractor:
    """
    Unified OCR extractor that tries PaddleOCR first, falls back to Tesseract.
    
    This class provides a consistent interface regardless of which OCR engine is available.
    """
    
    def __init__(self, languages: str = "nep+eng", use_gpu: bool = False, debug: bool = False):
        """
        Initialize OCR extractor with automatic engine selection.
        
        Args:
            languages: Language codes ("nep+eng", "hi", "en", etc.)
            use_gpu: Whether to use GPU (for PaddleOCR)
            debug: Enable debug mode
        """
        self.languages = languages
        self.use_gpu = use_gpu
        self.debug = debug
        self.engine_name = None
        self.extractor = None
        
        # Try PaddleOCR first
        try:
            from ocr.paddle_extractor import PaddleOCRExtractor
            # Map language codes
            lang_map = {
                "nep": "hi",
                "nep+eng": "hi+en",
                "eng": "en",
                "hi": "hi",
                "en": "en"
            }
            paddle_lang = lang_map.get(languages, "hi")
            self.extractor = PaddleOCRExtractor(languages=paddle_lang, use_gpu=use_gpu, debug=debug)
            self.engine_name = "paddleocr"
            logger.info("✅ Using PaddleOCR for extraction (better Nepali/Devanagari support)")
        except Exception as e:
            logger.warning(f"PaddleOCR not available ({e}), falling back to Tesseract")
            logger.info("💡 To use PaddleOCR, install: pip install paddleocr paddlepaddle")
            # Fallback to Tesseract
            try:
                self.extractor = TesseractExtractor(languages=languages, debug=debug)
                self.engine_name = "tesseract"
                logger.info("✅ Using Tesseract OCR for extraction")
            except Exception as e2:
                logger.error(f"Tesseract OCR also failed: {e2}")
                logger.error("Please install Tesseract: sudo pacman -S tesseract tesseract-data-nep")
                raise RuntimeError("No OCR engine available. Install PaddleOCR or Tesseract.")
    
    def extract_from_image(self, image_path: str, save_raw: bool = True) -> Dict[str, Any]:
        """Extract all text from image."""
        if self.engine_name == "paddleocr":
            return self.extractor.extract_full_text(image_path)
        else:
            return self.extractor.extract_from_image(image_path, save_raw=save_raw)
    
    def extract_fields(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields from template."""
        return self.extractor.extract_fields(image_path, template)
    
    def extract_from_template(self, image_path: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields from template (compatibility method)."""
        return self.extract_fields(image_path, template)
    
    def extract_full_text(self, image_path: str) -> Dict[str, Any]:
        """Extract full text (raw OCR result)."""
        if self.engine_name == "paddleocr":
            return self.extractor.extract_full_text(image_path)
        else:
            return self.extractor.extract_from_image(image_path, save_raw=True)
    
    def extract_field_bbox(self, image_path: str, bbox_px: List[int]) -> Dict[str, Any]:
        """Extract text from a specific bounding box."""
        if self.engine_name == "paddleocr":
            return self.extractor.extract_field_bbox(image_path, bbox_px)
        else:
            # Tesseract fallback - crop and extract
            img = cv2.imread(image_path)
            if img is None:
                raise FileNotFoundError(f"Image not found: {image_path}")
            x, y, w, h = map(int, bbox_px)
            region = img[y:y+h, x:x+w]
            if region.size == 0:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "bbox_px": bbox_px,
                    "bbox_mm": None,
                    "ocr_engine": "tesseract"
                }
            # Save temp image and run OCR
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                cv2.imwrite(tmp.name, region)
                result = self.extractor.extract_from_image(tmp.name, save_raw=False)
                os.unlink(tmp.name)
                text = result.get("full_text", "")
                confidences = [line.get("confidence", 0.0) for line in result.get("lines", [])]
                conf = float(np.mean(confidences)) if confidences else 0.0
                dpi = 300
                bbox_mm = [
                    round(bbox_px[0] * 25.4 / dpi, 2),
                    round(bbox_px[1] * 25.4 / dpi, 2),
                    round(bbox_px[2] * 25.4 / dpi, 2),
                    round(bbox_px[3] * 25.4 / dpi, 2)
                ]
                return {
                    "text": text,
                    "confidence": round(conf, 3),
                    "bbox_px": bbox_px,
                    "bbox_mm": bbox_mm,
                    "ocr_engine": "tesseract"
                }


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
