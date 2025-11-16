#!/bin/bash
# Auto Form Fill - CLI demo and smoke test

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  echo "✅ Virtual environment activated"
else
  echo "⚠️  Virtual environment not found. Creating one..."
  python -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  echo "📦 Installing dependencies..."
  pip install -q -r "$PROJECT_DIR/requirements.txt"
fi

OUTPUT_DIR="$PROJECT_DIR/output/demo"
mkdir -p "$OUTPUT_DIR"

echo "🧪 Running smoke test..."
echo ""

# Run smoke test using the CLI
python "$PROJECT_DIR/cli.py" \
  --images "$PROJECT_DIR/templates/business_front.jpg" \
  --template "$PROJECT_DIR/templates/business_tax_front.json" \
  --output "$OUTPUT_DIR" \
  --mode bbox

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Smoke test passed!"
  echo ""
  echo "📄 Generated files:"
  ls -lh "$OUTPUT_DIR"/*.pdf "$OUTPUT_DIR"/*.json 2>/dev/null || true
  echo ""
  echo "Next steps:"
  echo "  1) Start the API:    python main.py"
  echo "  2) Launch Streamlit: streamlit run app.py"
  echo "  3) Open http://localhost:8501"
  echo ""
  echo "✅ Demo completed successfully!"
else
  echo ""
  echo "❌ Smoke test failed. Check logs for details."
  exit 1
fi
