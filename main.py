#!/usr/bin/env python3
"""FastAPI backend for the Auto Form Fill MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from db import FormSubmission, get_session, init_db
from filler.form_filler import FormFiller
from ocr.extractor import OCRExtractor
from printer.pdf_generator import PDFGenerator
from utils.logger import get_logger

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
OUTPUT_DIR = BASE_DIR / "output" / "generated"

for directory in (UPLOAD_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

logger = get_logger(__name__)
form_filler = FormFiller()
pdf_generator = PDFGenerator()

init_db()

app = FastAPI(
    title="Auto Form Fill API",
    description="OCR + PDF generation backend for Nepali government forms.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FieldItem(BaseModel):
    id: str
    name: str
    text: str = ""
    confidence: float = 0.0
    bbox: Dict[str, Any] = Field(default_factory=dict)


class OCRResponse(BaseModel):
    template_id: str
    form_name: str
    image_path: str
    fields: List[FieldItem]
    validation: Dict[str, Any]


class SubmitRequest(BaseModel):
    template_id: str
    form_name: str
    image_path: str
    fields: List[FieldItem]


class SubmitResponse(BaseModel):
    submission_id: int
    pdf_path: str
    download_url: str
    validation: Dict[str, Any]


class TemplateSummary(BaseModel):
    id: str
    name: str
    form_type: Optional[str] = None
    description: Optional[str] = None
    image_filename: Optional[str] = None


def _resolve_template_path(template_id: str) -> Path:
    path = TEMPLATES_DIR / template_id
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return path


def _load_template(template_id: str) -> Dict[str, Any]:
    template_path = _resolve_template_path(template_id)
    return form_filler.load_template(str(template_path))


def _fields_dict_to_list(fields: Dict[str, Dict[str, Any]]) -> List[FieldItem]:
    items: List[FieldItem] = []
    for fid, data in fields.items():
        items.append(
            FieldItem(
                id=fid,
                name=data.get("name", fid),
                text=data.get("text", ""),
                confidence=float(data.get("confidence", 0.0)),
                bbox=data.get("bbox", {}),
            )
        )
    return items


def _fields_list_to_dict(items: List[FieldItem]) -> Dict[str, Dict[str, Any]]:
    return {
        item.id: {
            "name": item.name,
            "text": item.text,
            "confidence": float(item.confidence),
            "bbox": item.bbox,
        }
        for item in items
    }


def _template_metadata(template: Dict[str, Any]) -> Dict[str, Any]:
    if "forms" in template and template["forms"]:
        return template["forms"][0]
    return template


def _template_image_path(template: Dict[str, Any]) -> Optional[Path]:
    metadata = _template_metadata(template).get("metadata", {})
    image_filename = metadata.get("image_filename")
    if image_filename:
        candidate = TEMPLATES_DIR / image_filename
        if candidate.exists():
            return candidate
    return None


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@app.get("/templates", response_model=List[TemplateSummary], tags=["templates"])
def list_templates():
    templates: List[TemplateSummary] = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = form_filler.load_template(str(path))
            meta = _template_metadata(data)
            templates.append(
                TemplateSummary(
                    id=path.name,
                    name=meta.get("name", path.stem),
                    form_type=meta.get("form_type"),
                    description=meta.get("description"),
                    image_filename=meta.get("metadata", {}).get("image_filename"),
                )
            )
        except Exception as exc:
            logger.warning("Failed to load template %s: %s", path.name, exc)
    return templates


@app.post("/ocr", response_model=OCRResponse, tags=["processing"])
async def run_ocr(
    template_id: str = Form(...),
    file: UploadFile = File(...),
    use_semantic_matching: str = Form("false")
):
    """
    Run OCR on uploaded image and extract fields.
    
    Args:
        template_id: Template identifier
        file: Uploaded image file
        use_semantic_matching: "true" or "false" string to enable semantic field matching.
                              Useful for ID cards or documents without predefined regions.
    
    Returns:
        OCRResponse with extracted fields
    """
    template = _load_template(template_id)
    metadata = _template_metadata(template)
    form_name = metadata.get("name", template_id)

    unique_name = f"{uuid4().hex}_{file.filename}"
    image_path = UPLOAD_DIR / unique_name

    logger.info("Saving uploaded image to %s", image_path)
    contents = await file.read()
    image_path.write_bytes(contents)

    # Use PaddleOCR by default for better Nepali support
    # Can fallback to Tesseract if needed
    try:
        from ocr.paddle_extractor import PaddleOCRExtractor
        extractor = PaddleOCRExtractor(languages="hi", use_gpu=False, debug=False)
        logger.info("Using PaddleOCR for extraction (better Nepali/Devanagari support)")
    except Exception as e:
        logger.warning(f"PaddleOCR not available, falling back to Tesseract: {e}")
        from ocr.extractor import TesseractExtractor
        extractor = TesseractExtractor(languages="nep+eng", debug=False)
        logger.info("Using Tesseract OCR for extraction")
    
    # Convert string to boolean
    use_semantic = use_semantic_matching.lower() in ("true", "1", "yes", "on")
    
    if use_semantic:
        logger.info("Using semantic field matching mode")
        # Use semantic matching for ID cards or unstructured documents
        extracted = form_filler.extract_and_match_semantically(
            str(image_path),
            template,
            extractor,
            save_mapping=str(OUTPUT_DIR / f"{unique_name}_mapping.json")
        )
    else:
        logger.info("Using bbox-based template extraction mode")
        # Use traditional bbox-based extraction
        extracted = extractor.extract_from_template(str(image_path), template)
    
    validation = form_filler.validate_extracted_data(extracted, template)

    return OCRResponse(
        template_id=template_id,
        form_name=form_name,
        image_path=str(image_path),
        fields=_fields_dict_to_list(extracted),
        validation=validation,
    )


@app.post("/submit", response_model=SubmitResponse, tags=["processing"])
def submit_form(payload: SubmitRequest):
    template = _load_template(payload.template_id)
    extracted_dict = _fields_list_to_dict(payload.fields)

    validation = form_filler.validate_extracted_data(extracted_dict, template)
    pdf_data = form_filler.prepare_data_for_pdf(extracted_dict, template)

    template_image = _template_image_path(template)
    background_image = template_image or Path(payload.image_path)

    if not Path(payload.image_path).exists():
        raise HTTPException(status_code=400, detail="Uploaded image not found on server")

    pdf_path = OUTPUT_DIR / f"{uuid4().hex}.pdf"
    logger.info("Generating filled PDF at %s", pdf_path)

    pdf_generator.create_filled_pdf_from_image(
        str(background_image),
        pdf_data,
        str(pdf_path),
    )

    with get_session() as session:
        submission = FormSubmission(
            form_name=payload.form_name,
            template_id=payload.template_id,
            image_path=payload.image_path,
            pdf_path=str(pdf_path),
            fields_json=json.dumps(extracted_dict, ensure_ascii=False),
            validation_json=json.dumps(validation, ensure_ascii=False),
        )
        session.add(submission)
        session.flush()
        submission_id = submission.id

    download_url = f"/submissions/{submission_id}/pdf"

    return SubmitResponse(
        submission_id=submission_id,
        pdf_path=str(pdf_path),
        download_url=download_url,
        validation=validation,
    )


@app.get("/submissions", tags=["submissions"])
def list_submissions(limit: int = 20):
    with get_session() as session:
        records = (
            session.query(FormSubmission)
            .order_by(FormSubmission.created_at.desc())
            .limit(limit)
            .all()
        )
        return [record.to_dict() for record in records]


@app.get("/submissions/{submission_id}", tags=["submissions"])
def get_submission(submission_id: int):
    with get_session() as session:
        record = session.get(FormSubmission, submission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        return record.to_dict()


@app.get("/submissions/{submission_id}/pdf", response_class=FileResponse, tags=["submissions"])
def download_pdf(submission_id: int):
    with get_session() as session:
        record = session.get(FormSubmission, submission_id)
        if record is None or not record.pdf_path:
            raise HTTPException(status_code=404, detail="PDF not found")

        pdf_path = Path(record.pdf_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file missing on server")

    return FileResponse(path=pdf_path, filename=pdf_path.name, media_type="application/pdf")


@app.exception_handler(Exception)
async def global_exception_handler(_request, exc):  # type: ignore[override]
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
