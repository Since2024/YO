"""Streamlit UI for the FirstChild MVP."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent.parent))  # Adds YO root to path

from app import data_dir
from app.db import FormSubmission, get_session, init_db
from app.filler import prepare_pdf_fields
from app.gemini import GeminiExtractionError, extract_fields_from_images
from app.ocr import extract_fields_with_ocr
from app.printer import create_filled_pdf
from app.utils import (
    get_logger,
    list_template_files,
    load_template_file,
    template_fields,
    template_image_path,
)

st.set_page_config(page_title="FOMO MVP", layout="wide")

init_db()

if "runs" not in st.session_state:
    st.session_state.runs = []

logger = get_logger(__name__)
MAX_EXTRACTION_SECONDS = 60


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
        logger.info(
            "UI: Gemini extraction triggered for %d files (template=%s)",
            len(images_bytes),
            selected_template_path.name,
        )
        engine = "gemini"
        extraction = None
        start_time = time.perf_counter()
        with st.spinner("Extracting with Gemini (timeout 60s)..."):
            try:
                extraction = extract_fields_from_images(images_bytes, template)
            except GeminiExtractionError as exc:
                elapsed = time.perf_counter() - start_time
                logger.warning(
                    "UI: Gemini extraction failed after %.2fs: %s", elapsed, exc
                )
                st.warning(f"Gemini failed: {exc}. Falling back to OCR.")
                engine = "ocr"
                try:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                        tmp.write(uploaded_files[0].getvalue())
                        tmp.flush()
                        with st.spinner("Falling back to OCR..."):
                            extraction = extract_fields_with_ocr(tmp.name, template)
                except Exception as ocr_exc:
                    st.error(f"Both extraction methods failed: {ocr_exc}")
                    st.stop()
                finally:
                    if "tmp" in locals():
                        Path(tmp.name).unlink(missing_ok=True)
            finally:
                elapsed = time.perf_counter() - start_time

        if not extraction:
            st.error("Extraction failed")
            st.stop()

        st.session_state.current_extraction = {
            "engine": engine,
            "files": [file.name for file in uploaded_files],
            "extraction": extraction,
            "template_file": selected_template_path.name,
            "template_name": selected_template_label,
            "template_json": template,
        }
        st.success(f"✓ Extracted {len(extraction)} fields using {engine.upper()}")
        st.rerun()

# Editable review section
if "current_extraction" in st.session_state:
    st.markdown("---")
    st.subheader("📝 Review & Edit Extracted Data")

    run = st.session_state.current_extraction
    template = run["template_json"]
    extraction = run["extraction"]

    with st.form(key="edit_extraction_form"):
        st.write(f"**Template**: {run['template_name']}")
        st.write(f"**Source**: {', '.join(run['files'])}")
        st.write(f"**Engine**: {run['engine'].upper()}")

        edited_values: Dict[str, str] = {}

        st.markdown("#### 🏠 जग्गाधनी विवरण (Land Owner Details)")
        col1, col2 = st.columns(2)

        for field in template_fields(template):
            if field is None or not isinstance(field, dict):
                continue

            fid = field.get("id")
            if not fid:
                continue

            field_name = field.get("name", fid)
            field_label = field.get("label", field_name)
            field_desc = field.get("desc", "")
            current_value = extraction.get(fid, {}).get("value", "")
            confidence = extraction.get(fid, {}).get("confidence", 0.0)
            is_required = field.get("validate", {}).get("req", False)

            label = f"{field_name} {'*' if is_required else ''}"
            if confidence > 0:
                label += f" (confidence: {confidence:.0%})"

            target_col = None
            if fid in {"f001", "f002", "f003", "f004", "f005", "f006"}:
                target_col = col1
            elif fid in {"f007", "f008", "f009", "f010", "f011", "f012"}:
                target_col = col2

            target = target_col if target_col else st
            if field.get("type") == "text_date" or field.get("validate", {}).get("type") == "date":
                edited_value = target.date_input(
                    label,
                    value=None,
                    key=f"edit_{fid}",
                    help=field_desc or None,
                )
                edited_values[fid] = str(edited_value) if edited_value else current_value
            else:
                edited_values[fid] = target.text_input(
                    label,
                    value=current_value,
                    key=f"edit_{fid}",
                    help=field_desc or None,
                    placeholder=field_label,
                )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            submit_button = st.form_submit_button("💾 Save & Generate PDF", use_container_width=True)
        with col_cancel:
            cancel_button = st.form_submit_button("🔄 Extract Again", use_container_width=True)

        if submit_button:
            for fid, value in edited_values.items():
                if value is not None:
                    extraction[fid] = {
                        "value": value,
                        "confidence": extraction.get(fid, {}).get("confidence", 1.0),
                        "notes": (extraction.get(fid, {}).get("notes", "") + " [user-edited]").strip(),
                    }

            prepared = prepare_pdf_fields(extraction, template)

            if not prepared:
                st.error("No fields to save")
                st.stop()

            st.session_state.runs.insert(
                0,
                {
                    "engine": run["engine"],
                    "files": run["files"],
                    "extraction": extraction,
                    "prepared": prepared,
                    "template_file": run["template_file"],
                    "template_name": run["template_name"],
                    "template_json": template,
                },
            )

            artifacts = data_dir()
            base_name = f"ui_{len(st.session_state.runs)}_{run['files'][0].split('.')[0]}"
            pdf_path = artifacts / f"{base_name}.pdf"
            json_path = artifacts / f"{base_name}.json"

            background = template_image_path(template)
            if not background:
                st.error("Template background image missing")
                st.stop()

            create_filled_pdf(str(background), prepared, str(pdf_path))
            json_path.write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            _save_to_db(run["template_name"], run["template_file"], pdf_path, extraction, prepared)

            st.success(f"✓ PDF saved to {pdf_path}")

            del st.session_state.current_extraction
            st.rerun()

        if cancel_button:
            del st.session_state.current_extraction
            st.rerun()

if "current_extraction" not in st.session_state and not st.session_state.runs:
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

