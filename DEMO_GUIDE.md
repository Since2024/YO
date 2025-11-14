# 🎯 Demo Guide - Semantic Field Matching Feature

## Quick Demo Steps

### 1. Start the Backend (Terminal 1)
```bash
cd /home/npc/YO
source venv/bin/activate
python main.py
```
✅ Backend running on `http://localhost:8000`

### 2. Start the Frontend (Terminal 2)
```bash
cd /home/npc/YO
source venv/bin/activate
streamlit run app.py
```
✅ Frontend opens at `http://localhost:8501`

---

## 🎬 Demo Scenarios

### Scenario A: Traditional Bbox-Based Extraction (Default)
**Use Case:** Scanned form with predefined regions

1. Open Streamlit UI (`http://localhost:8501`)
2. Select template: **"सम्पत्ति तथा भूमिकर फारम"** (Land Tax Form)
3. Upload a scanned form image (e.g., `templates/business_front.jpg`)
4. **Leave "Use Semantic Field Matching" unchecked**
5. Click **"🔍 Run OCR"**
6. Show: Fields extracted based on bounding boxes from template
7. Review extracted values
8. Click **"✅ Validate & Save"**
9. Download the filled PDF

**What to Explain:**
- "This uses predefined bounding boxes from the template JSON"
- "Each field has exact pixel coordinates"
- "Works well for standardized forms"

---

### Scenario B: Semantic Field Matching (NEW FEATURE)
**Use Case:** National ID card or unstructured document

1. Open Streamlit UI (`http://localhost:8501`)
2. Select template: **"सम्पत्ति तथा भूमिकर फारम"** (Land Tax Form)
3. Upload a National ID card image (or any document with text like "नाम : हसन गाहा")
4. **✅ CHECK "🧠 Use Semantic Field Matching"**
5. Click **"🔍 Run OCR"**
6. Show: System intelligently matches OCR text to template fields
   - Example: "नाम : हसन गाहा" → Matches to "जग्गा/धनीको नाम र थर"
7. Review matched fields (show match scores if available)
8. Click **"✅ Validate & Save"**
9. Download the filled PDF

**What to Explain:**
- "This is the NEW semantic matching feature"
- "It understands Nepali field labels semantically"
- "No need for predefined bounding boxes"
- "Uses fuzzy matching and keyword dictionaries"
- "Perfect for ID cards, certificates, or unstructured documents"

---

## 📝 Demo Script (What to Say)

### Introduction
> "I've built an Auto Form Fill system that extracts data from Nepali government forms using OCR. Today I'm demonstrating a new feature: **Semantic Field Matching**."

### Show Traditional Method (Scenario A)
> "First, let me show the traditional approach. When you have a scanned form with predefined regions, the system extracts text from specific bounding boxes. This works well for standardized forms."

### Show Semantic Matching (Scenario B)
> "Now, here's the new feature. When you upload an ID card or unstructured document, the system can intelligently match fields. For example, if the ID card says 'नाम : हसन गाहा', it automatically maps this to the form field 'जग्गा/धनीको नाम र थर' - even though the labels are different."

### Technical Highlights
> "The system uses:
> - Keyword dictionaries for common Nepali field labels
> - Fuzzy string matching for partial matches
> - Category-based matching (e.g., all 'name' variants map together)
> - Confidence scoring to ensure accuracy"

### Conclusion
> "This makes the system much more flexible - you can now use it with ID cards, certificates, or any document, not just pre-templated forms."

---

## 🧪 Quick Test (CLI)

If you want to test semantic matching via command line:

```bash
cd /home/npc/YO
source venv/bin/activate

python << 'EOF'
from pathlib import Path
from filler.form_filler import FormFiller
from ocr.extractor import OCRExtractor
import json

# Load template
form_filler = FormFiller()
template = form_filler.load_template("templates/sampati_tax_page1_front.json")

# Extract OCR from image (full image, not bbox-based)
extractor = OCRExtractor(languages="nep+eng", debug=False)
ocr_result = extractor.extract_from_image("input/sample/id.jpg")

# Match semantically
matched = form_filler.match_ocr_to_template_semantically(
    ocr_result, 
    template,
    save_mapping="output/demo/semantic_mapping.json"
)

print("\n✅ Semantic Matching Results:")
print(json.dumps(matched, indent=2, ensure_ascii=False))
EOF
```

---

## 🎯 Key Points to Emphasize

1. **Problem Solved:** Traditional OCR requires exact bounding boxes. Semantic matching works with any document layout.

2. **How It Works:**
   - Parses OCR text (handles "नाम : हसन गाहा" format)
   - Matches field labels using keywords + fuzzy matching
   - Maps to template fields intelligently

3. **Real-World Use:** Perfect for processing ID cards, certificates, or documents where you don't have predefined regions.

4. **Accuracy:** Uses confidence thresholds and multiple matching strategies to ensure reliable results.

---

## 🐛 Troubleshooting

**Backend not starting?**
```bash
# Check if port 8000 is free
lsof -i :8000
# Or use different port in main.py
```

**Streamlit can't connect?**
- Verify backend is running on `http://localhost:8000`
- Check sidebar URL in Streamlit UI

**No templates showing?**
- Ensure `templates/*.json` files exist
- Check file permissions

**OCR not working?**
- Verify Tesseract is installed: `tesseract --version`
- Check Nepali language data: `ls tessdata/nep.traineddata`

---

## 📸 Sample Images

If you need test images:
- Use `templates/business_front.jpg` for traditional demo
- Use `input/sample/id.jpg` for semantic matching demo (if available)
- Or create a simple ID card image with text like:
  - "नाम : हसन गाहा"
  - "ठेगाना : काठमाण्डौ"
  - "राष्ट्रिय परिचय पत्र नं : 123456789"

---

**Good luck with your demo! 🚀**

