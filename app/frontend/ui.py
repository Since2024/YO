"""Streamlit UI for the FirstChild MVP."""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))  # Adds YO root to path
import json
import os
import tempfile
from pathlib import Path
from typing import List

import streamlit as st

from app import data_dir
from app.db import FormSubmission, get_session, init_db
from app.filler import prepare_pdf_fields
from app.gemini import GeminiExtractionError, extract_fields_from_images
from app.ocr import OCRFallbackError, extract_fields_with_ocr
from app.printer import create_filled_pdf
from app.utils import (
    list_template_files,
    load_template_file,
    template_image_path,
)

st.set_page_config(page_title="FOMO MVP", layout="wide")

init_db()

if "runs" not in st.session_state:
    st.session_state.runs = []


def _template_display_name(path: Path) -> str:
    template = load_template_file(path.name)
    if template.get("forms"):
        return f"{template['forms'][0].get('name', path.stem)} ({path.name})"
    return f"{template.get('name', path.stem)} ({path.name})"


def _save_to_db(template_name: str, template_file: str, pdf_path: Path, payload: dict, prepared: List[dict]):
    with get_session() as session:
        submission = FormSubmission(
            template_name=template_name,
            template_file=template_file,
            pdf_path=str(pdf_path),
            gemini_json=json.dumps(payload, ensure_ascii=False),
            normalized_fields=json.dumps(prepared, ensure_ascii=False),
        )
        session.add(submission)


st.title("🧾 FirstChild - Nepali Form Extraction")
st.caption("Gemini Vision + PDF filling + DB persistence")

if not os.getenv("GEMINI_API_KEY"):
    st.error("Set GEMINI_API_KEY in your environment to enable Gemini Vision.")

template_files = list_template_files()
if not template_files:
    st.warning("No templates found in app/templates.")
    st.stop()

template_choices = { _template_display_name(path): path for path in template_files }
selected_template_label = st.selectbox("Select template", list(template_choices.keys()))
selected_template_path = template_choices[selected_template_label]
template = load_template_file(selected_template_path.name)

uploaded_files = st.file_uploader(
    "Drag & drop form scans (JPG/PNG/PDF images)",
    type=["jpg", "jpeg", "png", "tif", "tiff"],
    accept_multiple_files=True,
)

col_preview, col_actions = st.columns([2, 1])
with col_preview:
    if uploaded_files:
        st.write("Preview")
        cols = st.columns(min(3, len(uploaded_files)))
        for idx, file in enumerate(uploaded_files):
            with cols[idx % len(cols)]:
                st.image(file, caption=file.name, use_column_width=True)

with col_actions:
    if st.button("🚀 Extract with Gemini", disabled=not uploaded_files):
        images_bytes = [file.getvalue() for file in uploaded_files]
        engine = "gemini"
        try:
            extraction = extract_fields_from_images(images_bytes, template)
        except GeminiExtractionError as exc:
            st.warning(f"Gemini failed: {exc}. Falling back to OCR.")
            if not uploaded_files:
                st.stop()
            engine = "ocr"
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(uploaded_files[0].getvalue())
                tmp.flush()
                try:
                    extraction = extract_fields_with_ocr(tmp.name, template)
                finally:
                    tmp.close()
                    Path(tmp.name).unlink(missing_ok=True)

        prepared = prepare_pdf_fields(extraction, template)
        st.session_state.runs.insert(
            0,
            {
                "engine": engine,
                "files": [file.name for file in uploaded_files],
                "extraction": extraction,
                "prepared": prepared,
                "template_file": selected_template_path.name,
                "template_name": selected_template_label,
                "template_json": template,
            },
        )
        st.success(f"Captured {len(prepared)} fields using {engine.upper()}")

if not st.session_state.runs:
    st.stop()

st.markdown("---")
st.subheader("Recent extractions")

for idx, run in enumerate(st.session_state.runs):
    with st.expander(f"{run['template_name']} — {', '.join(run['files'])}"):
        st.write(f"Engine: **{run['engine']}** • Fields: **{len(run['prepared'])}**")
        st.json(run["extraction"])

        cols = st.columns(3)
        with cols[0]:
            generate_clicked = st.button(
                "Generate PDF & Save",
                key=f"pdf_{idx}",
                disabled=not run["prepared"],
            )
        with cols[1]:
            st.write(f"Template file: `{run['template_file']}`")
        with cols[2]:
            st.write(f"Images: {len(run['files'])}")

        if generate_clicked:
            artifacts = data_dir()
            base_name = f"ui_{idx}_{run['files'][0].split('.')[0]}"
            pdf_path = artifacts / f"{base_name}.pdf"
            json_path = artifacts / f"{base_name}.json"

            background = template_image_path(run["template_json"])
            if not background:
                st.error("Template background image missing. Add metadata.image_filename.")
                continue

            create_filled_pdf(str(background), run["prepared"], str(pdf_path))
            json_path.write_text(
                json.dumps(run["extraction"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _save_to_db(run["template_name"], run["template_file"], pdf_path, run["extraction"], run["prepared"])

            st.success(f"Saved PDF to {pdf_path}")
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                key=f"download_{idx}",
            )

