#!/bin/bash

# Auto Form Fill - Demo Script
# Demonstrates the OCR-based form filling pipeline

set -e  # Exit on error

echo "======================================================================"
echo "          Auto Form Fill - MVP Demo Script"
echo "======================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"
echo ""

# Create necessary directories
mkdir -p data/input data/output logs

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please update .env with your MySQL credentials before running."
    echo ""
fi

echo "======================================================================"
echo "Demo 1: Business Tax Form (Front)"
echo "======================================================================"
echo ""

python3 main.py \
    --image templates/business_front.jpg \
    --template templates/business_tax_front.json \
    --output data/output/business_tax_front_filled.pdf \
    --data data/output/business_tax_front_data.json \
    --debug

echo ""
echo "✅ Business Tax Form (Front) Demo Completed!"
echo ""

echo "======================================================================"
echo "Demo 2: Sampati/Land Tax Form (Front)"
echo "======================================================================"
echo ""

python3 main.py \
    --image templates/sampati_front.jpg \
    --template templates/sampati_tax_page1_front.json \
    --output data/output/sampati_tax_front_filled.pdf \
    --data data/output/sampati_tax_front_data.json \
    --debug

echo ""
echo "✅ Sampati/Land Tax Form (Front) Demo Completed!"
echo ""

echo "======================================================================"
echo "🎉 All Demos Completed Successfully!"
echo "======================================================================"
echo ""
echo "📁 Output files:"
echo "  • data/output/business_tax_front_filled.pdf"
echo "  • data/output/business_tax_front_data.json"
echo "  • data/output/sampati_tax_front_filled.pdf"
echo "  • data/output/sampati_tax_front_data.json"
echo ""
echo "📊 Logs: logs/app_*.log"
echo ""
echo "======================================================================"
