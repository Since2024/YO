# Auto Form Fill – OCR + PDF Automation MVP

Automated pipeline for processing Nepali government forms. Upload a scanned form, run OCR (Tesseract with Nepali + English models), review and edit extracted data, store the validated payload in MySQL, and generate a filled PDF that can be downloaded or shared.

## ✨ Key Features

- **Template-driven OCR** – JSON templates define bounding boxes for each field on Business Tax and Land Tax forms.
- **Tesseract (nep+eng)** – Reliable text extraction for Nepali and English characters with bundled tessdata support.
- **FastAPI backend** – REST endpoints for OCR, validation, persistence, and PDF generation.
- **Streamlit frontend** – Minimal UI to upload images, review OCR results, edit values, and download filled PDFs.
- **MySQL via SQLAlchemy** – Stores submission history (`ocr_submissions`) with extracted data and PDF paths.
- **ReportLab PDF output** – Produces print-ready overlays on top of the original form template.
- **CLI demo script** – `run_demo.sh` runs the full pipeline on a bundled sample image without launching the web stack.

## 🗂 Project Structure

```
ocr/               # OCR extractor (pytesseract)
filler/            # Template loading, validation, data prep
printer/           # PDF generation utilities
db/                # SQLAlchemy models & session helpers
utils/             # Logging utilities
main.py            # FastAPI application (uvicorn entrypoint)
app.py             # Streamlit UI for the MVP
run_demo.sh        # CLI demo pipeline
requirements.txt   # Python dependencies
templates/         # JSON templates + reference images
data/              # Runtime data (uploads, etc.)
output/            # Generated PDFs & JSON outputs
```

## ⚙️ Prerequisites

- Python 3.10+
- Tesseract OCR with Nepali data:
  ```bash
  sudo pacman -S tesseract tesseract-data-nep
  ```
- MySQL server (or use SQLite fallback – see below)

## 🚀 Quick Start

1. **Clone & install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL credentials
   ```
   > Tip: set `DB_DRIVER=sqlite` to use a local SQLite database (`data/autoformfill.db`) when MySQL isn’t available.

3. **Run the backend (FastAPI)**
   ```bash
   python main.py
   # Server listens on http://localhost:8000
   ```

4. **Launch the frontend (Streamlit)**
   ```bash
   streamlit run app.py
   # Opens http://localhost:8501
   ```

5. **Demo the pipeline via CLI (optional)**
   ```bash
   ./run_demo.sh
   # Outputs: output/demo/demo_cli.pdf and demo_cli.json
   ```

## 🌐 API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET    | `/health` | Service health probe |
| GET    | `/templates` | List available JSON templates |
| POST   | `/ocr` | Run OCR on an uploaded image (multipart) |
| POST   | `/submit` | Validate, persist, and generate filled PDF |
| GET    | `/submissions` | Recent submissions (latest first) |
| GET    | `/submissions/{id}` | Submission metadata |
| GET    | `/submissions/{id}/pdf` | Download generated PDF |

## 🖥 Streamlit Workflow

1. Select a form template (Business Tax / Land Tax).
2. Upload the scanned form image.
3. Click **Run OCR** to populate fields automatically.
4. Review + edit any values directly in the UI.
5. Click **Validate & Save** to store data and generate the PDF.
6. Download the filled PDF with a single click.

Validation warnings and errors are surfaced immediately. All actions also log to the console via `utils/logger.py`.

## 🗄 Database Schema

`ocr_submissions`

| Column          | Type     | Notes |
| --------------- | -------- | ----- |
| `id`            | INT PK   | Auto increment |
| `form_name`     | VARCHAR  | Display name of template |
| `template_id`   | VARCHAR  | JSON template filename |
| `image_path`    | VARCHAR  | Stored upload path |
| `pdf_path`      | VARCHAR  | Generated PDF path |
| `fields_json`   | TEXT     | JSON payload of fields |
| `validation_json` | TEXT   | Validation summary |
| `created_at`    | DATETIME | UTC timestamp |

## 🧪 Testing the Core Pipeline

The CLI demo script uses the Business Tax front image:

```bash
./run_demo.sh
```

It prints extracted field JSON, validation results, and writes both a PDF overlay and a companion JSON file to `output/demo/`.

## 🛠 Troubleshooting

- **Tesseract cannot find `nep` / `eng`**: make sure the language data is installed or download `nep.traineddata` into the `tessdata/` folder (the backend automatically sets `TESSDATA_PREFIX`).
- **MySQL unavailable**: set `DB_DRIVER=sqlite` in `.env` to fall back to a local SQLite database for demos.
- **Streamlit cannot contact backend**: confirm `python main.py` is running on `http://localhost:8000` and update the sidebar URL if necessary.
- **PDF overlay misalignment**: verify the template JSON bounding boxes (`templates/*.json`) match the uploaded form resolution.

## 📄 License

MIT – see `LICENSE` if included.

---

