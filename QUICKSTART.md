# Quick Start Guide - Auto Form Fill MVP

## 🚀 Setup (5 minutes)

### 1. Install MySQL (if not already installed)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# Set root password
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';
FLUSH PRIVILEGES;
EXIT;
```

### 2. Configure Environment

```bash
cd /app

# Copy environment file
cp .env.example .env

# Edit with your MySQL credentials (if different)
nano .env
```

### 3. Install Python Dependencies

```bash
# If not in virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**Note**: First run will download PaddleOCR models (~200MB), takes 5-10 minutes.

## 🎬 Run Demo

```bash
chmod +x run_demo.sh
./run_demo.sh
```

This processes:
- Business Tax Form (Front)
- Sampati/Land Tax Form (Front)

Output: `data/output/`

## 📝 Manual Usage

### Single Form Processing

```bash
python main.py \
  --image templates/business_front.jpg \
  --template templates/business_tax_front.json \
  --output data/output/filled.pdf \
  --debug
```

### Without Database

```bash
python main.py \
  --image templates/business_front.jpg \
  --template templates/business_tax_front.json \
  --output data/output/filled.pdf \
  --no-db
```

## 🧪 Run Tests

```bash
python tests/smoke_test.py
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `ocr/extractor.py` | PaddleOCR implementation |
| `filler/form_filler.py` | Template mapping |
| `printer/pdf_generator.py` | PDF generation |
| `db/models.py` | Database CRUD operations |
| `.env` | Configuration |

## 🔍 Verify Installation

```bash
# Check dependencies
python -c "import paddleocr, pymysql, cv2; print('✅ All dependencies OK')"

# Test database connection
python -c "from db import init_database; init_database(); print('✅ Database OK')"

# Check template
python -c "from filler import FormFiller; f = FormFiller(); f.load_template('templates/business_tax_front.json'); print('✅ Template OK')"
```

## 📊 Output Structure

```
data/output/
├── business_tax_front_filled.pdf    # Filled PDF
├── business_tax_front_data.json     # Extracted data
├── sampati_tax_front_filled.pdf
└── sampati_tax_front_data.json
```

## 🛠️ Troubleshooting

### PaddleOCR download timeout
```bash
# Set timeout
export PIP_DEFAULT_TIMEOUT=1000
pip install paddleocr --upgrade
```

### MySQL connection refused
```bash
# Check MySQL is running
sudo systemctl status mysql

# Start if not running
sudo systemctl start mysql
```

### Low OCR accuracy
- Ensure input images are 300+ DPI
- Check template bbox coordinates
- Enable debug mode: `--debug`

## 📖 Full Documentation

See `README.md` for complete documentation.

## 🎯 Next Steps

1. Process your own forms
2. Create new templates (see template format in README)
3. Integrate with your workflow
4. Explore database CRUD operations

---

**Ready to automate!** 🚀
