# Deployment Report - Auto Form Fill MVP

## Overview

This report documents the production-quality MVP for OCR-based automatic filling of Nepali government forms (Business Tax and Land/Sampati forms).

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- Virtual environment (recommended)
- MySQL (optional, SQLite is used by default)
- Tesseract OCR with Nepali data (fallback if PaddleOCR not available)

### 2. Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Note: PaddleOCR installation may take a few minutes
# If PaddleOCR fails, Tesseract will be used as fallback
```

### 3. Database Setup

#### Option A: SQLite (Default - No setup needed)
The system will automatically create `data/autoformfill.db` if no MySQL configuration is provided.

#### Option B: MySQL
1. Create `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your MySQL credentials:
   ```env
   DB_DRIVER=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=your_username
   MYSQL_PASSWORD=your_password
   MYSQL_DB=autoformfill
   ```

3. Create database tables:
   ```bash
   python db/setup_db.py
   ```

### 4. Font Setup

The system will automatically download Noto Sans Devanagari font if not found locally. Font will be saved to `fonts/NotoSansDevanagari-Regular.ttf`.

## Running the Application

### CLI Mode (Batch Processing)

#### Single File Processing
```bash
python cli.py --images path/to/image.jpg --template templates/business_tax_front.json --output output/generated
```

#### Multiple Files
```bash
python cli.py --images img1.jpg img2.jpg img3.jpg --template templates/business_tax_front.json
```

#### Folder Processing
```bash
python cli.py --folder input/sample --template templates/business_tax_front.json --mode bbox --debug
```

#### CLI Options
- `--images`: One or more image file paths
- `--folder`: Process all images in a folder
- `--template`: Path to template JSON (required)
- `--output`: Output directory (default: `output/generated`)
- `--mode`: Extraction mode - `bbox` (template-based) or `semantic` (matching)
- `--debug`: Enable debug mode (saves debug images and raw OCR JSON)

### Streamlit UI Mode

1. Start the FastAPI backend:
   ```bash
   python main.py
   # Server runs on http://localhost:8000
   ```

2. In another terminal, start Streamlit:
   ```bash
   streamlit run app.py
   # UI opens at http://localhost:8501
   ```

3. In the Streamlit UI:
   - Select a template (Business Tax or Land Tax)
   - Upload one or more images
   - Review and edit extracted fields
   - Export to PDF or save to database

### Demo Script

Run the demo script:
```bash
./run_demo.sh
```

This will:
- Activate the virtual environment
- Run a smoke test on sample images
- Start the Streamlit app for demo

## Example Commands

### Batch Processing Example
```bash
# Process all images in a folder with debug output
python cli.py --folder data/uploads --template templates/business_tax_front.json --mode bbox --debug --output output/batch_results
```

### Single File with Semantic Matching
```bash
# Use semantic matching for ID cards or unstructured documents
python cli.py --images input/sample/id.jpg --template templates/business_tax_front.json --mode semantic
```

## Key Features

### 1. OCR Engine
- **Primary**: PaddleOCR (better Nepali/Devanagari support)
- **Fallback**: Tesseract OCR (if PaddleOCR not available)
- Automatic language detection and multi-language support (Nepali + English)

### 2. Image Processing
- Automatic deskewing and rotation correction
- Template alignment using feature matching (ORB/AKAZE)
- DPI-aware coordinate conversion

### 3. PDF Generation
- Embedded Nepali font (Noto Sans Devanagari)
- Blue color for filled text (distinguishes from printed text)
- Support for box_grid (one character per cell)
- Support for table rendering
- Signature image insertion

### 4. Database
- Improved schema with separate tables:
  - `form_templates`: Template definitions
  - `submissions`: Submission records
  - `extracted_fields`: Individual field data with confidence and review flags
- Backward compatible with legacy `ocr_submissions` table

### 5. Validation
- Configurable confidence threshold (default: 0.7)
- Automatic field validation (phone, date, email, etc.)
- `needs_review` flag for low-confidence fields

## Fallbacks and Limitations

### OCR Engine Fallback
- If PaddleOCR is not installed, the system automatically falls back to Tesseract
- Clear error messages guide users to install missing dependencies
- Both engines support Nepali + English multi-language recognition

### Font Fallback
- If Noto Sans Devanagari is not found locally, it will be downloaded automatically
- If download fails, system uses Helvetica (Nepali text may not render correctly)

### Image Alignment
- If template alignment fails, system still attempts direct bbox extraction
- Misalignment warnings are logged for manual review

### Database
- Defaults to SQLite for easy local development
- MySQL can be configured via environment variables
- Both `DB_*` and `MYSQL_*` environment variable formats are supported

## Limitations

1. **OCR Accuracy**: OCR accuracy depends on image quality. Low-quality scans may require manual correction.

2. **Template Alignment**: Complex rotations or severe distortions may cause alignment failures.

3. **Font Rendering**: Some complex Nepali characters may not render perfectly if font download fails.

4. **Batch Processing**: Large batches may take significant time. Consider processing in smaller chunks.

## Suggested Next Steps

1. **Performance Optimization**:
   - Add GPU support for PaddleOCR (set `use_gpu=True`)
   - Implement parallel processing for batch operations
   - Add caching for template loading

2. **Accuracy Improvements**:
   - Train custom OCR models for specific form types
   - Implement post-processing for common OCR errors
   - Add confidence-based re-extraction

3. **UI Enhancements**:
   - Add image preview with bbox overlays
   - Implement field-level confidence visualization
   - Add batch review interface

4. **Integration**:
   - Add API authentication
   - Implement webhook notifications
   - Add export to other formats (Excel, CSV)

5. **Testing**:
   - Expand test coverage
   - Add integration tests
   - Performance benchmarking

## Troubleshooting

### PaddleOCR Installation Issues
```bash
# Try CPU-only installation
pip install paddlepaddle==2.6.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install paddleocr==2.7.3
```

### Tesseract Not Found
```bash
# Arch Linux
sudo pacman -S tesseract tesseract-data-nep

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-nep

# macOS
brew install tesseract tesseract-lang
```

### Database Connection Issues
- Check `.env` file configuration
- Verify MySQL server is running
- Test connection with: `python db/setup_db.py`

### Font Issues
- Check `fonts/` directory exists
- Verify internet connection for font download
- Manually download font from: https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari

## File Structure

```
.
├── cli.py                 # CLI entrypoint for batch processing
├── main.py               # FastAPI backend
├── app.py                # Streamlit frontend
├── requirements.txt      # Pinned dependencies
├── run_demo.sh          # Demo script
├── DEPLOY_REPORT.md     # This file
├── ocr/
│   ├── extractor.py     # Unified OCR extractor (PaddleOCR + Tesseract)
│   └── paddle_extractor.py  # PaddleOCR implementation
├── utils/
│   ├── image_processing.py  # Image alignment, deskew, rotation
│   └── logger.py        # Logging utilities
├── filler/
│   └── form_filler.py   # Form filling with needs_review flag
├── printer/
│   └── pdf_generator.py  # PDF generation with Nepali font
├── db/
│   ├── models.py        # Database models (improved schema)
│   ├── connection.py    # Database connection
│   └── setup_db.py     # Database setup script
├── templates/           # Form templates (JSON + images)
└── output/             # Generated PDFs and JSONs
    ├── generated/      # CLI output
    ├── raw/            # Debug OCR JSON
    └── debug/          # Debug images
```

## Support

For issues or questions:
1. Check logs in `logs/app_YYYYMMDD.log`
2. Run with `--debug` flag for detailed output
3. Review error messages for corrective actions

---

**Version**: 1.0  
**Last Updated**: 2024  
**Status**: Production-Ready MVP

