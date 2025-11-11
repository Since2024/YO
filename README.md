# Auto Form Fill - OCR-based PDF Form Filling Tool

[![Status](https://img.shields.io/badge/status-MVP-green)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

A comprehensive Python CLI application designed for automated form filling using Tesseract OCR. Extracts data from scanned documents and fills official PDF forms for Nepali government forms (Business Tax, Land/Sampati Tax).

## 🎯 Project Overview

This MVP application automates the complete pipeline for form filling:
- **Input**: Scanned form images (JPG/PNG)
- **OCR**: Multi-language text extraction (English + Devanagari)
- **Extraction**: Structured field-based data extraction
- **Validation**: Field validation against templates
- **Storage**: MySQL database for form history
- **Output**: Filled PDF forms

## 🛠️ Tech Stack

- **Language**: Python 3.8+
- **OCR Engine**: Tesseract OCR (pytesseract) with Nepali + English support
- **PDF Generation**: ReportLab + OpenCV/PIL
- **Image Processing**: OpenCV, Pillow
- **Database**: MySQL with pymysql
- **Configuration**: python-dotenv

## 📁 Project Structure

```
/app/
├── main.py                    # CLI orchestrator
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── run_demo.sh               # Demo script
│
├── ocr/                      # OCR processing
│   ├── __init__.py
│   └── extractor.py          # Tesseract OCR implementation
│
├── filler/                   # Form filling logic
│   ├── __init__.py
│   └── form_filler.py        # Template mapping & validation
│
├── printer/                  # PDF export utilities
│   ├── __init__.py
│   └── pdf_generator.py      # ReportLab PDF generation
│
├── db/                       # Database layer
│   ├── __init__.py
│   ├── connection.py         # MySQL connection utils
│   └── models.py             # Database models (CRUD operations)
│
├── utils/                    # Utilities
│   ├── __init__.py
│   └── logger.py             # Logging configuration
│
├── templates/                # JSON templates
│   ├── business_tax_front.json
│   ├── business_tax_back.json
│   ├── sampati_tax_page1_front.json
│   ├── sampati_tax_page2_back.json
│   ├── business_front.jpg
│   ├── business_back.jpg
│   ├── sampati_front.jpg
│   └── sampati_last.jpg
│
├── data/
│   ├── input/                # Raw form images
│   └── output/               # Generated results
│
├── logs/                     # Application logs
│   └── app_*.log
│
└── tests/                    # Test suite
    ├── __init__.py
    └── smoke_test.py         # End-to-end smoke tests
```

## 🚀 Installation

### Prerequisites

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **MySQL Server**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mysql-server
   
   # macOS
   brew install mysql
   
   # Start MySQL
   sudo systemctl start mysql  # Linux
   brew services start mysql   # macOS
   ```

### Setup

1. **Clone the repository**:
   ```bash
   cd /app
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL credentials
   nano .env
   ```

5. **Initialize database**:
   The database and tables will be created automatically on first run.

## 📝 Configuration (.env)

```env
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=auto_form_fill

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO

# Paths
TEMPLATES_DIR=/app/templates
DATA_INPUT_DIR=/app/data/input
DATA_OUTPUT_DIR=/app/data/output
LOGS_DIR=/app/logs

# OCR Configuration
OCR_LANGUAGES=en,hi
OCR_USE_GPU=False
```

## 🖥️ Usage

### Basic Command

```bash
python main.py --image <input_image> --template <template_json> --output <output_pdf>
```

### Command Line Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--image` | `-i` | Yes | Path to input form image (JPG/PNG) |
| `--template` | `-t` | Yes | Path to JSON template file |
| `--output` | `-o` | Yes | Path for output filled PDF |
| `--data` | | No | Path to save extracted data JSON |
| `--languages` | `-l` | No | OCR languages (default: en,hi) |
| `--debug` | `-d` | No | Enable debug mode |
| `--no-db` | | No | Skip database storage |

### Examples

1. **Business Tax Form (Front)**:
   ```bash
   python main.py \
     --image templates/business_front.jpg \
     --template templates/business_tax_front.json \
     --output data/output/business_filled.pdf \
     --debug
   ```

2. **Sampati/Land Tax Form (Front)**:
   ```bash
   python main.py \
     --image templates/sampati_front.jpg \
     --template templates/sampati_tax_page1_front.json \
     --output data/output/sampati_filled.pdf
   ```

3. **With custom data output**:
   ```bash
   python main.py \
     --image templates/business_front.jpg \
     --template templates/business_tax_front.json \
     --output data/output/filled.pdf \
     --data data/output/extracted.json
   ```

## 🎬 Run Demo

Run the automated demo script to test both forms:

```bash
chmod +x run_demo.sh
./run_demo.sh
```

This will process:
- Business Tax Form (Front)
- Sampati/Land Tax Form (Front)

Output files will be saved in `data/output/`

## 📊 System Workflow

```
┌─────────────────┐
│  Input Image    │
│   (JPG/PNG)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Preprocessing  │
│  (OpenCV)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OCR Extract    │
│  (Tesseract OCR)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Template Match  │
│  (Field Map)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Save to MySQL  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Generate PDF   │
│  (ReportLab)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Output PDF +   │
│  JSON Data      │
└─────────────────┘
```

## 🧪 Testing

### Run Smoke Tests

```bash
python tests/smoke_test.py
```

Tests include:
- Database connection
- OCR initialization
- Template loading
- End-to-end pipeline

## 📄 Template Format

Templates are JSON files defining field positions and OCR parameters:

```json
{
  "forms": [{
    "name": "Form Name",
    "form_type": "business_tax",
    "fields": [
      {
        "id": "f001",
        "name": "field_name",
        "label": "Field Label",
        "type": "text_line",
        "page": 1,
        "bbox": {
          "px": [x, y, width, height],
          "mm": [x_mm, y_mm, width_mm, height_mm]
        },
        "ocr": {
          "lang": "nep",
          "psm": 7
        },
        "validate": {
          "req": true,
          "type": "string",
          "min_len": 2
        }
      }
    ]
  }]
}
```

## 🗄️ Database Schema

### Tables

1. **form_templates**: Template definitions
2. **form_processings**: Processing history
3. **extracted_data**: OCR extracted field data

### CRUD Operations

```python
from db import FormTemplate, FormProcessing, ExtractedData

# Create template
template_id = FormTemplate.create(name, form_type, path, fields_json)

# Create processing
processing_id = FormProcessing.create(template_id, input_file)

# Save extracted data
ExtractedData.bulk_create(processing_id, data_list)

# Query
processings = FormProcessing.get_all(limit=50)
data = ExtractedData.get_by_processing_id(processing_id)
```

## 🔧 Troubleshooting

### Common Issues

1. **Tesseract OCR not found**:
   - Install Tesseract: `sudo pacman -S tesseract tesseract-data-nep`
   - Verify: `tesseract --version`
   - Check pytesseract can find it: `python -c "import pytesseract; print(pytesseract.get_tesseract_version())"`

2. **MySQL connection error**:
   - Check MySQL is running: `sudo systemctl status mysql`
   - Verify credentials in `.env`
   - Ensure database exists or will be created

3. **Low OCR accuracy**:
   - Ensure input image is high resolution (300+ DPI)
   - Check template bbox coordinates match the form
   - Enable debug mode to inspect cropped regions

4. **Missing dependencies**:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

## 📈 Performance Tips

- **Image Quality**: Use 300+ DPI scans for best results
- **Preprocessing**: Images are automatically preprocessed (grayscale, denoise, threshold)
- **GPU Acceleration**: Set `OCR_USE_GPU=True` in `.env` if CUDA available
- **Batch Processing**: Process multiple forms by scripting main.py calls

## 🚀 Future Enhancements

- [ ] Web API (Flask/FastAPI) for remote form submission
- [ ] Automatic template generation from form images
- [ ] Multi-page PDF support
- [ ] Template versioning
- [ ] Dashboard for result visualization
- [ ] Firebase backup integration
- [ ] Advanced validation rules

## 📝 Logging

Logs are saved to `logs/app_YYYYMMDD.log` with the following levels:
- **DEBUG**: Detailed processing information
- **INFO**: General progress updates
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures

View logs:
```bash
tail -f logs/app_$(date +%Y%m%d).log
```

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
3. Review logs in `logs/` directory
4. Check template format and coordinates

---

**Auto Form Fill** - Automating Nepali government form filling with precision and efficiency.
