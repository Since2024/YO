#!/bin/bash
# Quick start script for demo

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Starting Auto Form Fill Demo..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python -m venv venv
fi

# Activate venv
source venv/bin/activate

# Check dependencies
echo "📦 Checking dependencies..."
if ! python -c "import streamlit, fastapi, pytesseract" 2>/dev/null; then
    echo "⚠️  Some dependencies missing. Installing..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Start the backend (Terminal 1):"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "2. Start the frontend (Terminal 2):"
echo "   source venv/bin/activate"
echo "   streamlit run app.py"
echo ""
echo "3. Open browser: http://localhost:8501"
echo ""
echo "📖 See DEMO_GUIDE.md for detailed demo instructions"
echo ""

