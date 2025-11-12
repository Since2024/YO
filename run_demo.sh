#!/bin/bash
# Auto Form Fill - CLI demo

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  echo "✅ Virtual environment activated"
fi

OUTPUT_DIR="$PROJECT_DIR/output/demo"
mkdir -p "$OUTPUT_DIR"

python <<'PY'
from pathlib import Path
import json
from filler.form_filler import FormFiller
from ocr.extractor import OCRExtractor
from printer.pdf_generator import PDFGenerator

project_dir = Path(__file__).resolve().parent
image_path = project_dir / "templates" / "business_front.jpg"
template_path = project_dir / "templates" / "business_tax_front.json"
output_pdf = project_dir / "output" / "demo" / "demo_cli.pdf"
output_json = output_pdf.with_suffix('.json')

form_filler = FormFiller()
template = form_filler.load_template(str(template_path))

extractor = OCRExtractor(languages="nep+eng", debug=False)
extracted = extractor.extract_from_template(str(image_path), template)

validation = form_filler.validate_extracted_data(extracted, template)
pdf_data = form_filler.prepare_data_for_pdf(extracted, template)

form_filler.save_extracted_json(extracted, str(output_json))

pdf_generator = PDFGenerator()
pdf_generator.create_filled_pdf_from_image(str(image_path), pdf_data, str(output_pdf))

print("OCR extracted fields:")
print(json.dumps(extracted, ensure_ascii=False, indent=2))
print("\nValidation:")
print(json.dumps(validation, ensure_ascii=False, indent=2))
print(f"\n📄 Filled PDF saved to: {output_pdf}")
print(f"📊 Extracted JSON saved to: {output_json}")
PY

echo ""
echo "Next steps:"
echo "  1) Start the API:    python main.py"
echo "  2) Launch Streamlit: streamlit run app.py"
echo "  3) Open http://localhost:8501"
echo ""
echo "✅ Demo completed successfully!"
