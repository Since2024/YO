# FirstChild - OCR-based PDF Form Filling Tool

FirstChild is a comprehensive Python CLI application designed for automated form filling using OCR (Optical Character Recognition) technology. It extracts data from scanned documents and fills official PDF forms with pixel-perfect positioning.

## 🎯 Project Overview

The application is specifically designed for automating form filling for fixed-format business tax and land/property tax forms where scanned data must be mapped to specific positions on official form PDFs.

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **OCR Engine**: pytesseract with custom configuration
- **PDF Generation**: ReportLab for pixel-perfect positioning
- **Image Processing**: OpenCV, Pillow, pdf2image
- **Template Format**: JSON schema with exact coordinates

## 📁 Project Structure

```
FirstChild/
├── main.py                  # CLI entry point
├── filler/                  # Core processing modules
│   ├── __init__.py
│   ├── ocr.py              # OCR extraction logic
│   ├── generate_pdf.py     # ReportLab PDF generator
│   ├── preprocess.py       # Image/PDF preprocessing
│   └── template_loader.py  # JSON template loader & validator
├── templates/              # Form templates
│   ├── business_tax.json
│   └── land_tax.json
├── input/
│   └── samples/            # Sample input files
├── output/
│   └── filled_forms/       # Generated filled PDFs
├── requirements.txt
└── README.md
```

## 🚀 Installation

### Prerequisites

1. **Python 3.11+** - Download from [python.org](https://python.org)

2. **Tesseract OCR** - Required for text extraction
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # macOS
   brew install tesseract
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Poppler** (for PDF processing)
   ```bash
   # Ubuntu/Debian  
   sudo apt-get install poppler-utils
   
   # macOS
   brew install poppler
   
   # Windows
   # Download from: http://blog.alivate.com.au/poppler-windows/
   ```

### Setup

1. **Clone or extract the project**:
   ```bash
   cd FirstChild/
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python main.py --help
   ```

## 📝 Template Format

Templates are JSON files that define field positions and OCR parameters:

```json
{
  "name": "Form Template Name",
  "description": "Template description",
  "version": "1.0",
  "fields": [
    {
      "name": "field_name",
      "x": 150,                 # X coordinate in points
      "y": 200,                 # Y coordinate in points  
      "width": 300,             # Field width in points
      "height": 25,             # Field height in points
      "page": 1,                # Page number (1-indexed)
      "ocr_psm": 7,            # OCR Page Segmentation Mode
      "description": "Field description"
    }
  ]
}
```

### Coordinate System
- **Origin**: Top-left corner (0,0)
- **Units**: Points (1 point = 1/72 inch)
- **X-axis**: Left to right
- **Y-axis**: Top to bottom

### OCR PSM Modes
- `6`: Uniform block of text (default)
- `7`: Single text line  
- `8`: Single word
- `9`: Single character
- `10`: Single character, circled

## 🖥️ Usage

### Basic Command Structure
```bash
python main.py --input <input_file> --template <template_file> --output <output_file>
```

### Examples

1. **Process a business tax form**:
   ```bash
   python main.py \
     --input input/samples/business_tax_scan.pdf \
     --template templates/business_tax.json \
     --output output/filled_forms/business_tax_filled.pdf
   ```

2. **Process a land tax form with debug mode**:
   ```bash
   python main.py \
     --input input/samples/land_tax_scan.jpg \
     --template templates/land_tax.json \
     --output output/filled_forms/land_tax_filled.pdf \
     --debug
   ```

3. **Process with Hindi OCR**:
   ```bash
   python main.py \
     --input input/samples/hindi_form.pdf \
     --template templates/business_tax.json \
     --output output/filled_forms/hindi_filled.pdf \
     --lang hin
   ```

### Command Line Options

| Option | Short | Required | Description |
|--------|--------|----------|-------------|
| `--input` | `-i` | Yes | Path to input PDF or image file |
| `--template` | `-t` | Yes | Path to JSON template file |
| `--output` | `-o` | Yes | Path for output filled PDF |
| `--lang` | `-l` | No | OCR language code (default: eng) |
| `--debug` | `-d` | No | Enable debug mode with detailed logging |

## 📊 System Workflow

1. **Input Processing**: Convert PDFs to images, normalize resolution
2. **Template Loading**: Load and validate JSON template
3. **OCR Extraction**: Extract text from defined field regions
4. **Confidence Analysis**: Calculate OCR confidence scores
5. **PDF Generation**: Create filled PDF with extracted data
6. **Output**: Save filled PDF and extraction results (JSON)

## 🔧 Configuration

### OCR Configuration
Default OCR configuration: `--oem 3 --psm 6`
- **OEM 3**: LSTM OCR engine
- **PSM 6**: Uniform block of text

### Image Processing
- **Default DPI**: 300 for PDF conversion
- **Target Width**: 2480 pixels for normalization
- **Processing**: Adaptive thresholding, Gaussian blur for noise reduction

## 📄 Output Files

The application generates two types of output:

1. **Filled PDF** (`output_path`): The final filled form
2. **Extraction Results** (`output_path.json`): OCR data for auditing

### Extraction Results Format
```json
{
  "field_name": {
    "text": "Extracted Text",
    "confidence": 95.2,
    "coordinates": {"x": 150, "y": 200, "width": 300, "height": 25},
    "ocr_config": "--oem 3 --psm 7"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Tesseract not found**:
   - Ensure Tesseract is installed and in PATH
   - On Windows, add Tesseract installation directory to PATH

2. **PDF conversion fails**:
   - Install poppler-utils (Linux) or poppler (macOS)
   - On Windows, ensure poppler binaries are in PATH

3. **Low OCR accuracy**:
   - Adjust `ocr_psm` values in template
   - Ensure input images are high resolution (300+ DPI)
   - Check field coordinates match actual form layout

4. **Memory issues with large PDFs**:
   - Reduce DPI in preprocessing (default: 300)
   - Process pages individually for very large documents

### Debug Mode

Enable debug mode with `--debug` flag to:
- View detailed processing logs
- Save cropped field images for inspection
- Display OCR confidence scores
- Get full error traceback

## 📖 Template Creation Guide

1. **Get a sample form**: Scan or obtain digital copy of the form
2. **Identify field positions**: Use image editor to find coordinates
3. **Create template JSON**: Define fields with exact coordinates
4. **Test and refine**: Run extraction and adjust coordinates as needed
5. **Optimize OCR settings**: Adjust `ocr_psm` values for better accuracy

### Tips for Better Templates
- Use higher DPI scans (300+) for coordinate accuracy
- Ensure field dimensions are slightly larger than text areas
- Test with multiple sample documents
- Use appropriate OCR PSM modes for different field types

## 🔍 Performance Optimization

- **Image Resolution**: Higher DPI improves OCR accuracy but increases processing time
- **Field Size**: Slightly oversized field regions improve text capture
- **OCR PSM**: Use specific PSM modes for different text types:
  - PSM 7 for single lines
  - PSM 8 for single words  
  - PSM 6 for paragraphs

## 📜 License

This project is provided for educational and development purposes. Please ensure compliance with applicable laws and regulations when processing official documents.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Enable debug mode for detailed error information
3. Review template format and coordinate system
4. Ensure all dependencies are properly installed

---

**FirstChild** - Automating form filling with precision and efficiency.