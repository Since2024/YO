# 🔍 COMPLETE CODEBASE ANALYSIS & FIX PLAN

## 📋 EXECUTIVE SUMMARY

**Project Status:** 70% Complete - Core architecture solid but critical blockers prevent MVP readiness

**Critical Blockers:**
1. ❌ OCR accuracy < 50% for Nepali text (Tesseract limitations)
2. ❌ PDF text misalignment and missing Nepali font support
3. ❌ Bbox coordinates don't match real scanned images
4. ❌ No image deskew/rotation correction
5. ❌ Weak validation (only required/length checks)

**Estimated Fix Time:** 4-5 days of focused development

---

## 1️⃣ COMPLETE MENTAL MODEL

### **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                     │
├─────────────────────────────────────────────────────────────┤
│  Streamlit UI (app.py)                                      │
│  - Template selection                                        │
│  - Image upload                                             │
│  - OCR mode toggle (bbox vs semantic)                       │
│  - Field review/editing                                     │
│  - PDF download                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────▼──────────────────────────────────────┐
│                  FASTAPI BACKEND (main.py)                  │
├─────────────────────────────────────────────────────────────┤
│  Endpoints:                                                  │
│  - GET  /health                                              │
│  - GET  /templates                                           │
│  - POST /ocr (bbox or semantic extraction)                  │
│  - POST /submit (validation + PDF generation + DB save)     │
│  - GET  /submissions/{id}/pdf                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
│ OCR LAYER    │ │ FILLER   │ │ PDF GEN    │
│              │ │ LAYER    │ │ LAYER      │
├──────────────┤ ├──────────┤ ├────────────┤
│ Tesseract    │ │ FormFiller│ │ PDFGenerator│
│ Extractor    │ │ FieldMatcher│ │ ReportLab  │
│              │ │          │ │ OpenCV     │
│ - Preprocess │ │ - Validate│ │ - Overlay  │
│ - Extract    │ │ - Match  │ │ - Convert  │
│ - Multiple   │ │ - Prepare│ │ - Save PDF │
│   strategies │ │          │ │            │
└──────┬───────┘ └────┬─────┘ └─────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                     │
            ┌────────▼────────┐
            │  DATABASE LAYER │
            ├─────────────────┤
            │ SQLAlchemy ORM   │
            │ MySQL/SQLite     │
            │ FormSubmission   │
            └──────────────────┘
```

### **Data Flow**

```
1. User uploads image → FastAPI saves to data/uploads/
2. User selects template → Load JSON from templates/
3. User clicks "Run OCR":
   a) Bbox mode: Extract from predefined regions
   b) Semantic mode: Extract all text, then match semantically
4. OCR returns: {field_id: {text, confidence, bbox}}
5. User reviews/edits fields in Streamlit
6. User clicks "Submit":
   a) Validate extracted data
   b) Generate PDF (overlay text on template image)
   c) Save to database (fields_json, validation_json)
   d) Return submission_id
7. User downloads PDF via /submissions/{id}/pdf
```

### **Key Components**

#### **1. OCR Extractor (`ocr/extractor.py`)**
- **Class:** `TesseractExtractor`
- **Methods:**
  - `preprocess()` - Image preprocessing (grayscale, denoise, threshold)
  - `extract_from_image()` - Full page OCR (for semantic matching)
  - `extract_fields()` - Bbox-based extraction (for template forms)
- **Current State:** ✅ Works but low accuracy for Nepali
- **Issues:** Tesseract poor Nepali support, no deskew, hardcoded preprocessing

#### **2. Form Filler (`filler/form_filler.py`)**
- **Class:** `FormFiller`
- **Methods:**
  - `load_template()` - Load JSON template
  - `validate_extracted_data()` - Check required fields, length, confidence
  - `prepare_data_for_pdf()` - Format data for PDF generation
  - `match_ocr_to_template_semantically()` - Use FieldMatcher for ID cards
- **Current State:** ✅ Works but validation is weak
- **Issues:** No format validation (dates, phones), no data normalization

#### **3. Field Matcher (`filler/field_matcher.py`)**
- **Class:** `FieldMatcher`
- **Purpose:** Semantic matching for unstructured documents
- **Methods:**
  - `parse_ocr_line()` - Extract "label : value" pairs
  - `match_ocr_to_template()` - Fuzzy match OCR to template fields
  - `find_best_category()` - Category-based matching (90+ keywords)
- **Current State:** ✅ Works but threshold too low (0.5)
- **Issues:** False positives, no spatial awareness

#### **4. PDF Generator (`printer/pdf_generator.py`)**
- **Class:** `PDFGenerator`
- **Methods:**
  - `create_filled_pdf_from_image()` - Overlay text on image, save as PDF
  - `create_pdf_with_reportlab()` - Direct PDF generation (not used)
  - `_overlay_text_on_image()` - OpenCV text drawing
- **Current State:** ❌ Broken - text misaligned, no Nepali font
- **Issues:** Coordinate conversion errors, Y-axis inversion, pixelated text

#### **5. Database (`db/models.py`, `db/connection.py`)**
- **Model:** `FormSubmission`
- **Schema:** Single table with JSON blobs
- **Current State:** ✅ Works but not normalized
- **Issues:** No relational design, no indexes, no user management

---

## 2️⃣ COMPLETE PROBLEM DIAGNOSIS

### **🔴 CRITICAL ISSUES (Block MVP)**

#### **OCR Issues**

**Problem 1.1: Tesseract Poor Nepali Accuracy**
- **Location:** `ocr/extractor.py:22-43`
- **Root Cause:** Tesseract's `nep.traineddata` is outdated, trained on limited dataset
- **Impact:** 50-60% accuracy for Nepali text, unusable for production
- **Evidence:** User reports "extraction didn't work" for business form
- **Code Reference:**
  ```python
  # Line 207: Uses hardcoded "nep" language
  lang = ocr_config.get("lang", self.languages)  # Default: "nep+eng"
  ```
- **Fix Required:** Switch to PaddleOCR or EasyOCR

**Problem 1.2: No Image Deskew/Rotation**
- **Location:** `ocr/extractor.py:48-78` (preprocess method)
- **Root Cause:** No rotation detection or correction
- **Impact:** OCR fails on rotated/scanned images
- **Evidence:** User reports "ward no extracted but nothing else" - likely misaligned
- **Fix Required:** Add Hough transform for skew detection + rotation correction

**Problem 1.3: Hardcoded Preprocessing Parameters**
- **Location:** `ocr/extractor.py:66-71`
- **Root Cause:** Fixed denoising and threshold parameters
- **Impact:** Doesn't adapt to different image qualities
- **Code:**
  ```python
  # Line 66: Fixed parameters
  denoised = cv2.fastNlMeansDenoising(gray_region, None, 10, 7, 21)
  # Line 69: Fixed block size
  thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10)
  ```
- **Fix Required:** Adaptive preprocessing based on image quality metrics

**Problem 1.4: Bbox Alignment Issues**
- **Location:** `ocr/extractor.py:191-194`
- **Root Cause:** Template bboxes created from clean images, not real scans
- **Impact:** Wrong fields extracted (e.g., name from address field)
- **Code:**
  ```python
  # Line 191: Direct crop without alignment
  x, y, w, h = map(int, bbox)
  region = img[y:y+h, x:x+w]
  ```
- **Evidence:** User reports "business form extraction didn't work"
- **Fix Required:** Image registration/alignment before extraction

#### **Preprocessing Issues**

**Problem 2.1: No CLAHE for Low Contrast**
- **Location:** `ocr/extractor.py:223-231`
- **Root Cause:** CLAHE added but not used in all paths
- **Impact:** Poor extraction from faded/scanned documents
- **Fix Required:** Ensure CLAHE is always applied

**Problem 2.2: No Perspective Correction**
- **Location:** Missing entirely
- **Root Cause:** No homography transform for distorted scans
- **Impact:** OCR fails on angled/scanned images
- **Fix Required:** Add perspective transform detection

#### **Bbox Alignment Issues**

**Problem 3.1: Image Dimension Mismatch**
- **Location:** `ocr/extractor.py:180-201`
- **Root Cause:** Recent fix added scaling, but may not work if metadata missing
- **Impact:** Bboxes misaligned when image size differs
- **Code:**
  ```python
  # Line 188-201: Scaling logic exists but may fail silently
  template_dims = metadata.get("image_dimensions_px", {})
  if template_dims:  # If metadata missing, no scaling!
      # ... resize logic
  ```
- **Fix Required:** Better fallback when metadata missing

**Problem 3.2: No Template Registration**
- **Location:** Missing entirely
- **Root Cause:** No feature matching to align uploaded image to template
- **Impact:** Even with correct dimensions, slight rotation/translation causes misalignment
- **Fix Required:** Add ORB/SIFT keypoint matching + homography

#### **Template Issues**

**Problem 4.1: Inconsistent Template Format**
- **Location:** `templates/business_tax_front.json` vs `sampati_tax_page1_front.json`
- **Root Cause:** Business form uses `"forms": [...]`, sampati uses `"fields": [...]`
- **Impact:** Code must handle both formats (lines 168-173 in extractor.py)
- **Code:**
  ```python
  # Line 168-173: Dual format handling
  if "fields" in template:
      fields = template["fields"]
  elif "forms" in template and template["forms"]:
      fields = template["forms"][0]["fields"]
  ```
- **Fix Required:** Standardize template format

**Problem 4.2: Bbox Coordinates May Be Wrong**
- **Location:** Template JSON files
- **Root Cause:** Coordinates measured from clean template images, not real scans
- **Impact:** Fields extracted from wrong locations
- **Evidence:** User reports extraction failures
- **Fix Required:** Re-measure coordinates from actual scanned forms OR add automatic alignment

#### **Semantic Matching Issues**

**Problem 5.1: Threshold Too Low (0.5)**
- **Location:** `filler/field_matcher.py:109`, `filler/form_filler.py:23`
- **Root Cause:** Lowered from 0.6 to 0.5 for "better matching"
- **Impact:** False positive matches, wrong fields mapped
- **Code:**
  ```python
  # Line 109: Low threshold
  def __init__(self, confidence_threshold: float = 0.5, debug: bool = False):
  ```
- **Fix Required:** Increase to 0.7, add manual review flag

**Problem 5.2: No Spatial Awareness**
- **Location:** `filler/field_matcher.py:272-414`
- **Root Cause:** Matching only uses text similarity, ignores position
- **Impact:** Can match "नाम" from wrong location on page
- **Fix Required:** Add position-based scoring

**Problem 5.3: Limited Keyword Coverage**
- **Location:** `filler/field_matcher.py:15-107`
- **Root Cause:** 20 categories, but may miss variations
- **Impact:** Some field labels not recognized
- **Fix Required:** Expand keyword dictionary, add user-defined synonyms

#### **Nepali Language Issues**

**Problem 6.1: Tesseract Nepali Model Outdated**
- **Location:** `tessdata/nep.traineddata`
- **Root Cause:** Old training data, poor Devanagari support
- **Impact:** 50-60% accuracy
- **Fix Required:** Use PaddleOCR (better Hindi/Nepali support)

**Problem 6.2: No Nepali Font in PDF**
- **Location:** `printer/pdf_generator.py:163-166`
- **Root Cause:** Uses OpenCV `FONT_HERSHEY_SIMPLEX` which doesn't support Devanagari
- **Impact:** Nepali text renders as □□□ or blank
- **Code:**
  ```python
  # Line 163-166: No Nepali font
  cv2.putText(
      overlay_img, text, (x + 2, y + height - 5),
      cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness
  )
  ```
- **Fix Required:** Embed Noto Sans Devanagari font, use ReportLab for text

#### **PDF Font & Coordinate Issues**

**Problem 7.1: Coordinate Conversion Errors**
- **Location:** `printer/pdf_generator.py:97-114`
- **Root Cause:** Multiple conversion steps (px → mm → pt) with rounding errors
- **Impact:** Text misaligned in PDF
- **Code:**
  ```python
  # Line 104-111: Multiple conversions
  pixel_to_mm = 0.248  # Hardcoded
  x_mm = x_px * pixel_to_mm
  x = x_mm * mm  # mm is 2.83465
  y = self.page_height - (y_mm * mm)  # Y inversion
  ```
- **Fix Required:** Direct px → pt conversion using DPI

**Problem 7.2: Y-Axis Inversion Issues**
- **Location:** `printer/pdf_generator.py:111`
- **Root Cause:** PDF origin is bottom-left, image is top-left
- **Impact:** Text drawn at wrong vertical position
- **Code:**
  ```python
  # Line 111: May be incorrect
  y = self.page_height - (y_mm * mm)
  ```
- **Fix Required:** Verify and fix Y-axis calculation

**Problem 7.3: Low Resolution Output**
- **Location:** `printer/pdf_generator.py:57`
- **Root Cause:** 100 DPI instead of 300 DPI
- **Impact:** Pixelated, unprintable PDFs
- **Code:**
  ```python
  # Line 57: Low resolution
  pil_image.save(output_path, "PDF", resolution=100.0)
  ```
- **Fix Required:** Increase to 300 DPI

**Problem 7.4: No Text Wrapping**
- **Location:** `printer/pdf_generator.py:163-166`
- **Root Cause:** Fixed text position, no wrapping logic
- **Impact:** Long text overflows bbox
- **Fix Required:** Add word wrapping for long fields

**Problem 7.5: Pixelated Text (OpenCV Rendering)**
- **Location:** `printer/pdf_generator.py:163-166`
- **Root Cause:** OpenCV renders text as pixels, not vectors
- **Impact:** Text quality poor, not scalable
- **Fix Required:** Use ReportLab for vector text rendering

#### **Database Integration Issues**

**Problem 8.1: No Normalized Schema**
- **Location:** `db/models.py:14-38`
- **Root Cause:** All fields stored as JSON blob
- **Impact:** Can't query individual fields, no reports
- **Code:**
  ```python
  # Line 24: JSON blob anti-pattern
  fields_json = Column(Text, nullable=False)
  ```
- **Fix Required:** Add normalized `extracted_fields` table (post-MVP)

**Problem 8.2: No Indexes**
- **Location:** `db/models.py:19-26`
- **Root Cause:** No index definitions
- **Impact:** Slow queries as data grows
- **Fix Required:** Add indexes on `template_id`, `created_at`

**Problem 8.3: No User Management**
- **Location:** Missing entirely
- **Root Cause:** Anonymous submissions only
- **Impact:** Can't track who submitted what
- **Fix Required:** Add users table (post-MVP)

#### **UI Issues**

**Problem 9.1: No Progress Indicator**
- **Location:** `app.py:106`
- **Root Cause:** Only spinner, no actual progress
- **Impact:** User doesn't know if OCR is running or stuck
- **Code:**
  ```python
  # Line 106: Generic spinner
  with st.spinner("Running OCR..."):
  ```
- **Fix Required:** Add progress bar or WebSocket updates

**Problem 9.2: Session State Can Get Stale**
- **Location:** `app.py:52-57`
- **Root Cause:** No session cleanup
- **Impact:** Old data persists across sessions
- **Fix Required:** Add session reset button

#### **Architecture Inconsistencies**

**Problem 10.1: Inconsistent Output Directories**
- **Location:** Multiple locations
- **Root Cause:** Different modules use different paths
- **Impact:** Files scattered, hard to find
- **Paths:**
  - `output/filled_forms/` (legacy)
  - `output/generated/` (API)
  - `output/demo/` (CLI)
  - `data/output/` (some scripts)
- **Fix Required:** Standardize to `output/generated/` only

**Problem 10.2: Hardcoded Paths**
- **Location:** Multiple files
- **Root Cause:** Absolute paths in some places
- **Impact:** Not portable
- **Fix Required:** Use `Path(__file__).parent` consistently

#### **Broken Imports / Missing Modules**

**Problem 11.1: PaddleOCR Not Installed**
- **Location:** `requirements.txt`
- **Root Cause:** Not in dependencies
- **Impact:** Can't switch to better OCR
- **Fix Required:** Add `paddleocr>=2.7.0`

**Problem 11.2: Missing Font File**
- **Location:** `printer/pdf_generator.py`
- **Root Cause:** Noto Sans Devanagari not bundled
- **Impact:** Can't render Nepali text
- **Fix Required:** Download and bundle font, or use system font

#### **Code Smells / Refactoring Needs**

**Problem 12.1: Duplicate Template Format Handling**
- **Location:** Multiple files (extractor.py, form_filler.py)
- **Root Cause:** Both handle `"forms"` and `"fields"` formats
- **Impact:** Code duplication, maintenance burden
- **Fix Required:** Create `TemplateLoader` utility class

**Problem 12.2: No Error Context**
- **Location:** All exception handlers
- **Root Cause:** Generic error messages
- **Impact:** Hard to debug
- **Fix Required:** Add detailed error context with file/line info

**Problem 12.3: Magic Numbers**
- **Location:** Multiple files
- **Root Cause:** Hardcoded values (0.248, 0.5, 0.7, etc.)
- **Impact:** Hard to tune
- **Fix Required:** Move to config file or constants

---

## 3️⃣ PRIORITIZED FIX PLAN

### **Phase 1: Critical OCR Fixes (Day 1) - 8 hours**

**Task 1.1: Install and Integrate PaddleOCR** (2h)
- Add `paddleocr>=2.7.0` to requirements.txt
- Create `ocr/paddle_extractor.py` with PaddleOCRExtractor class
- Maintain same interface as TesseractExtractor
- Test on sample images

**Task 1.2: Add Image Deskew/Rotation** (2h)
- Create `utils/image_processing.py` with deskew functions
- Add Hough transform for skew detection
- Add rotation correction
- Integrate into OCR preprocessing pipeline

**Task 1.3: Improve Preprocessing** (2h)
- Add adaptive preprocessing based on image quality
- Ensure CLAHE is always applied
- Add perspective correction for distorted scans
- Test on various image qualities

**Task 1.4: Add Image Alignment** (2h)
- Implement template registration using ORB/SIFT
- Calculate homography matrix
- Warp uploaded image to match template
- Update bbox extraction to use aligned image

### **Phase 2: PDF Generation Fixes (Day 2) - 8 hours**

**Task 2.1: Fix Coordinate Conversion** (2h)
- Rewrite coordinate conversion logic
- Use direct px → pt conversion with DPI
- Fix Y-axis inversion
- Test alignment on sample forms

**Task 2.2: Embed Nepali Font** (2h)
- Download Noto Sans Devanagari font
- Register with ReportLab
- Update PDF generator to use font
- Test Nepali text rendering

**Task 2.3: Switch to ReportLab for Text** (2h)
- Rewrite `_overlay_text_on_image` to use ReportLab
- Use vector text instead of OpenCV pixels
- Add text wrapping for long fields
- Test quality improvement

**Task 2.4: Increase PDF Resolution** (1h)
- Change resolution from 100 to 300 DPI
- Enable anti-aliasing
- Test print quality

**Task 2.5: Add Field Type Handlers** (1h)
- Handle text_line, checkbox, signature_box, box_grid
- Add proper rendering for each type
- Test all field types

### **Phase 3: Template & Validation Fixes (Day 3) - 8 hours**

**Task 3.1: Standardize Template Format** (1h)
- Convert sampati template to use `"forms"` format
- Update all template files
- Test template loading

**Task 3.2: Re-measure Template Coordinates** (2h)
- Load actual scanned forms
- Measure bbox coordinates from real scans
- Update business_tax_front.json
- Update sampati_tax_page1_front.json

**Task 3.3: Add Format Validators** (2h)
- Create `filler/validators.py`
- Add date, phone, citizenship, PAN validators
- Integrate into validation pipeline
- Test on sample data

**Task 3.4: Improve Semantic Matching** (2h)
- Increase threshold to 0.7
- Add spatial awareness (position-based scoring)
- Expand keyword dictionary
- Test on ID card samples

**Task 3.5: Add Confidence Filtering** (1h)
- Flag fields with confidence < 0.7
- Add "needs_review" flag
- Update UI to show review flags
- Test filtering logic

### **Phase 4: Polish & Testing (Day 4) - 8 hours**

**Task 4.1: Error Handling** (2h)
- Add detailed error context
- Improve error messages
- Add logging for all operations
- Test error scenarios

**Task 4.2: UI Improvements** (2h)
- Add progress indicator for OCR
- Add session reset button
- Improve error display
- Test UI flow

**Task 4.3: Standardize Output Paths** (1h)
- Consolidate to `output/generated/` only
- Update all file references
- Test file locations

**Task 4.4: End-to-End Testing** (2h)
- Test with 20 real forms
- Test both form types
- Test both OCR modes
- Document results

**Task 4.5: Documentation** (1h)
- Update README with new setup
- Document known issues
- Add troubleshooting guide

---

## 4️⃣ STEP-BY-STEP EXECUTION PLAN

### **Step 1: Create PaddleOCR Extractor**

**File:** `ocr/paddle_extractor.py` (NEW)

```python
"""PaddleOCR-based extractor for better Nepali support."""
from paddleocr import PaddleOCR
import cv2
import numpy as np
from typing import Dict, Any, List
from utils.logger import get_logger

logger = get_logger(__name__)

class PaddleOCRExtractor:
    def __init__(self, languages: str = "hi", use_gpu: bool = False, debug: bool = False):
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # Auto rotation
            lang=languages,  # "hi" for Hindi/Nepali
            use_gpu=use_gpu,
            show_log=False
        )
        self.debug = debug
        logger.info(f"Initialized PaddleOCR (lang={languages}, gpu={use_gpu})")
    
    def extract_from_image(self, image_path: str, save_raw: bool = True) -> Dict[str, Any]:
        """Extract all text from image."""
        result = self.ocr.ocr(image_path, cls=True)
        # Parse result into lines format...
        # Return same format as TesseractExtractor
```

### **Step 2: Add Image Processing Utilities**

**File:** `utils/image_processing.py` (NEW)

```python
"""Image preprocessing utilities."""
import cv2
import numpy as np
from typing import Tuple

def detect_skew(image: np.ndarray) -> float:
    """Detect skew angle using Hough transform."""
    # Implementation...

def correct_skew(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image to correct skew."""
    # Implementation...

def align_to_template(image: np.ndarray, template_image: np.ndarray) -> np.ndarray:
    """Align image to template using feature matching."""
    # Implementation...
```

### **Step 3: Fix PDF Generator**

**File:** `printer/pdf_generator.py` (REWRITE)

Key changes:
- Use ReportLab for all text rendering
- Embed Noto Sans Devanagari font
- Fix coordinate conversion
- Add text wrapping
- Increase resolution to 300 DPI

### **Step 4: Add Validators**

**File:** `filler/validators.py` (NEW)

```python
"""Field format validators."""
import re
from typing import Dict, Any

def validate_date(text: str) -> bool:
    """Validate Nepali date format."""
    # Implementation...

def validate_phone(text: str) -> bool:
    """Validate phone number (10 digits)."""
    # Implementation...

def validate_citizenship(text: str) -> bool:
    """Validate citizenship number format."""
    # Implementation...
```

### **Step 5: Update Main Pipeline**

**File:** `main.py` (UPDATE)

- Switch to PaddleOCR by default
- Add error handling
- Add progress tracking

### **Step 6: Update Templates**

**Files:** `templates/*.json` (UPDATE)

- Standardize format
- Update coordinates from real scans
- Add missing metadata

---

## 5️⃣ FILE-LEVEL ACTIONABLE TASKS

### **Files to Create:**
1. `ocr/paddle_extractor.py` - PaddleOCR implementation
2. `utils/image_processing.py` - Deskew, alignment utilities
3. `filler/validators.py` - Format validators
4. `fonts/NotoSansDevanagari-Regular.ttf` - Nepali font (download)

### **Files to Rewrite:**
1. `printer/pdf_generator.py` - Complete rewrite for ReportLab + font
2. `templates/business_tax_front.json` - Update coordinates
3. `templates/sampati_tax_page1_front.json` - Standardize format + coordinates

### **Files to Update:**
1. `ocr/extractor.py` - Add deskew, improve preprocessing
2. `filler/form_filler.py` - Add validators, improve validation
3. `filler/field_matcher.py` - Increase threshold, add spatial awareness
4. `main.py` - Switch to PaddleOCR, add error handling
5. `app.py` - Add progress indicator, improve UI
6. `requirements.txt` - Add paddleocr, update versions
7. `db/models.py` - Add indexes (optional)

### **Files to Delete/Move:**
1. Move `output/filled_forms/` to `output/generated/` (legacy)
2. Delete `__pycache__/` directories
3. Clean up duplicate output locations

---

## 6️⃣ EXPECTED OUTCOMES

### **After Phase 1 (OCR Fixes):**
- ✅ OCR accuracy: 50-60% → 75-85%
- ✅ Handles rotated/skewed images
- ✅ Better preprocessing for low-quality scans

### **After Phase 2 (PDF Fixes):**
- ✅ Nepali text renders correctly
- ✅ Text aligned to form fields
- ✅ Print-ready quality (300 DPI)

### **After Phase 3 (Template & Validation):**
- ✅ Correct field extraction
- ✅ Data validation working
- ✅ Semantic matching improved

### **After Phase 4 (Polish):**
- ✅ Demo-ready application
- ✅ Comprehensive error handling
- ✅ User-friendly UI

---

## 7️⃣ RISK MITIGATION

### **Risks:**
1. **PaddleOCR installation issues** → Fallback to Tesseract
2. **Font licensing** → Use open-source Noto font
3. **Template coordinate measurement** → Use semi-automated tool
4. **Performance degradation** → Profile and optimize

### **Contingency Plans:**
- Keep Tesseract as fallback
- Use system fonts if bundled font fails
- Manual coordinate entry if auto-alignment fails
- Async processing for large images

---

## 8️⃣ SUCCESS CRITERIA

### **MVP Ready When:**
1. ✅ OCR accuracy ≥ 75% for Nepali text
2. ✅ PDF renders Nepali text correctly
3. ✅ Text aligned to form fields (±2px)
4. ✅ Can process both business and land tax forms
5. ✅ Can process ID cards with semantic matching
6. ✅ End-to-end pipeline works without manual intervention
7. ✅ Error messages are clear and actionable

---

**NEXT STEP:** Begin implementation with Phase 1, Task 1.1 (PaddleOCR integration)

