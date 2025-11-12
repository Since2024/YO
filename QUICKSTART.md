# Quick Start Guide - Auto Form Fill MVP

## 1. Install prerequisites

```bash
sudo pacman -S tesseract tesseract-data-nep
# or use your distro's package manager
```

(Optional) install MySQL and create a database, or plan to use the SQLite fallback described below.

## 2. Setup project

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with DB credentials or switch to SQLite
```

To use SQLite (recommended for quick local demos):
```
DB_DRIVER=sqlite
DB_PATH=data/autoformfill.db
```

## 3. Launch services

Start the FastAPI backend:
```bash
python main.py
```
Backend listens on `http://localhost:8000`.

In a new terminal (same virtualenv), start the Streamlit UI:
```bash
streamlit run app.py
```
Open the provided URL (default `http://localhost:8501`).

## 4. Demo workflow

1. Select a JSON template in the sidebar.
2. Upload a scanned form image (Business Tax / Land Tax).
3. Click **Run OCR** to auto-populate fields.
4. Review & edit values if needed.
5. Click **Validate & Save** to persist and generate the PDF.
6. Download the filled PDF using the provided button.

## 5. CLI smoke test

Run the bundled demo without the UI:
```bash
./run_demo.sh
```
Outputs are placed in `output/demo/`.

## 6. Troubleshooting

- **Tesseract errors (`language not found`)**: make sure `nep.traineddata` exists. The repo bundles a `tessdata/` folder and sets `TESSDATA_PREFIX` automatically.
- **Database connection issues**: confirm credentials in `.env` or switch to SQLite.
- **Streamlit cannot reach backend**: ensure `python main.py` is running and the sidebar URL matches (`http://localhost:8000`).

## 7. Helpful commands

```bash
# Smoke tests
python tests/smoke_test.py

# Verify dependencies
python -c "import pytesseract, sqlalchemy, cv2; print('✅ Ready!')"
```

For full documentation, architecture, and API details, see `README.md`.
