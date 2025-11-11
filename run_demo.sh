#!/bin/bash

# Auto Form Fill - Demo Script
# Simple demo for Tesseract OCR-based form filling

set -e  # Exit on error

echo "======================================================================"
echo "          Auto Form Fill - Demo Script"
echo "======================================================================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: venv not found. Using system Python."
    echo "   Consider creating a venv: python3 -m venv venv"
fi

# Create necessary directories
mkdir -p data/output output logs

echo ""
echo "======================================================================"
echo "Running Demo: Business Tax Form"
echo "======================================================================"
echo ""

python main.py \
    --image ./templates/business_front.jpg \
    --template ./templates/business_tax_front.json \
    --output ./output/demo_filled.pdf \
    --no-db

echo ""
echo "✅ Demo completed successfully!"
echo ""
echo "📁 Output files:"
echo "  • output/demo_filled.pdf"
echo "  • output/demo_filled.json"
echo ""
echo "======================================================================"
