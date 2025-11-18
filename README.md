# FirstChild – Gemini-powered Nepali Form Extractor

Minimal MVP that turns batches of Nepali government forms into structured JSON, filled PDFs, and database records. Gemini Vision handles semantic extraction, OCR provides a local fallback, ReportLab renders the output, and both CLI + Streamlit UI share the same pipeline.

## Highlights

- **Gemini Vision 1.5 Flash** for semantic mapping (`app/gemini/extractor.py`).
- **OCR fallback** (Tesseract/OpenCV) whenever Gemini is unavailable.
- **Template-driven normalization** in `app/filler/form_filler.py`.
- **ReportLab + Noto Sans Devanagari** PDF generator with simple style hooks.
- **SQLAlchemy + MySQL/SQLite** persistence via `app/db`.
- **One CLI + Streamlit UI** calling the same core functions.

Repository layout (only the files that remain after cleanup):

```
app/
  gemini/         # Gemini Vision wrapper
  filler/         # Value normalization
  printer/        # PDF generation
  ocr/            # Lightweight OCR fallback
  utils/          # Template helpers + logging
  db/             # SQLAlchemy models + session helpers
  templates/      # JSON templates + reference images
  frontend/       # Streamlit UI
main.py           # CLI entry point
requirements.txt
README.md
```

Run artifacts (JSON/PDF) are written to `./artifacts/` automatically.

## Prerequisites

- Python 3.11+ (tested on 3.13).
- Tesseract with Nepali data: `sudo pacman -S tesseract tesseract-data-nep`.
- MySQL 8+ (or skip and let SQLite handle local testing).
- GOOGLE API access: set `GEMINI_API_KEY`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GEMINI_API_KEY=xxxxxxxxxxxxxxxx
export MYSQL_HOST=localhost      # optional, SQLite used when unset
export MYSQL_USER=formfill
export MYSQL_PASSWORD=secret
export MYSQL_DB=firstchild
```

The database tables are created automatically the first time you run the CLI/UI.

## CLI – Multi-image extraction

```
python main.py extract \
  --images input/sample/id.jpg input/sample/sample_business_tax.png \
  --template business_tax_front.json \
  --output-name demo_business
```

What happens:

1. Every image is passed to Gemini Vision along with the template schema.
2. If Gemini fails, the first image runs through the OCR fallback.
3. Output JSON + filled PDF land in `artifacts/demo_business.(json|pdf)`.
4. A `form_submissions` row stores raw + normalized payload.

List templates at any time:

```
python main.py templates
```

## Streamlit UI

```
streamlit run app/frontend/ui.py
```

Capabilities:

- Drag/drop multiple images.
- Live preview and Gemini extraction with OCR fallback.
- Inspect the JSON payload.
- Generate PDF + save to DB with one click.

## Environment Variables

| Name             | Description                                      |
| ---------------- | ------------------------------------------------ |
| `GEMINI_API_KEY` | Required. Google Generative AI key               |
| `GEMINI_MODEL`   | Optional. Defaults to `gemini-1.5-flash`         |
| `DATABASE_URL`   | Optional full SQLAlchemy URL                     |
| `MYSQL_*`/`DB_*` | Optional components for building a MySQL URL     |
| `SQLITE_PATH`    | Optional path for SQLite fallback                |
| `LOG_LEVEL`      | INFO by default                                  |

## Tests

A single smoke test (`app/utils/smoke_test.py`) covers the CLI wiring. Run with:

```
pytest app/utils/smoke_test.py
```

## Troubleshooting

- **Missing template background**: add `metadata.image_filename` inside the template JSON and place the referenced image under `app/templates/`.
- **Gemini quota or auth errors**: confirm `GEMINI_API_KEY` and check Google Cloud quotas.
- **ReportLab font download blocked**: manually download `NotoSansDevanagari-Regular.ttf` into `app/printer/fonts/`.
- **MySQL unavailable**: omit the MySQL env vars and SQLite will be used automatically.

## License

MIT (see repository root if provided).
