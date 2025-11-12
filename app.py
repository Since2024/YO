"""Streamlit frontend for the Auto Form Fill MVP."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Dict, List

import requests
import streamlit as st

st.set_page_config(page_title="Auto Form Fill", layout="wide")

BACKEND_DEFAULT = "http://localhost:8000"


def fetch_templates(api_url: str) -> List[Dict]:
    try:
        response = requests.get(f"{api_url}/templates", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to load templates: {exc}")
        return []


def run_ocr(api_url: str, template_id: str, uploaded_file) -> Dict:
    files = {
        "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")
    }
    data = {"template_id": template_id}
    response = requests.post(f"{api_url}/ocr", data=data, files=files, timeout=60)
    response.raise_for_status()
    return response.json()


def submit_form(api_url: str, payload: Dict) -> Dict:
    response = requests.post(f"{api_url}/submit", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def download_pdf(api_url: str, download_url: str) -> bytes:
    response = requests.get(f"{api_url}{download_url}", timeout=60)
    response.raise_for_status()
    return response.content


if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "edited_fields" not in st.session_state:
    st.session_state.edited_fields = {}
if "last_submission" not in st.session_state:
    st.session_state.last_submission = None


st.title("🧾 Auto Form Fill MVP")
st.caption("Upload Nepali government forms, verify OCR results, and export filled PDFs.")

with st.sidebar:
    st.header("Backend Settings")
    backend_url = st.text_input("FastAPI URL", BACKEND_DEFAULT)
    st.markdown("---")

    st.header("Template")
    templates = fetch_templates(backend_url)
    template_options = {tpl["name"]: tpl for tpl in templates}
    selected_template_name = st.selectbox(
        "Choose template",
        options=list(template_options.keys()) if template_options else [],
    )

    if st.button("📄 Refresh Templates"):
        st.experimental_rerun()

if not template_options:
    st.warning("No templates found. Place JSON templates inside the `templates/` directory.")
    st.stop()

selected_template = template_options[selected_template_name]

template_id = selected_template["id"]
form_name = selected_template_name or template_id

st.subheader("1. Upload Form Image")
uploaded_file = st.file_uploader(
    "Drag & drop a scanned form (JPG/PNG)",
    type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
)

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded image", use_column_width=True)

    if st.button("🔍 Run OCR", type="primary"):
        with st.spinner("Running OCR..."):
            try:
                ocr_result = run_ocr(backend_url, template_id, uploaded_file)
                st.session_state.ocr_result = ocr_result
                st.session_state.edited_fields = {
                    field["id"]: field.get("text", "") for field in ocr_result["fields"]
                }
                st.session_state.last_submission = None
                st.success("OCR completed. Review and edit below.")
            except Exception as exc:
                st.error(f"OCR failed: {exc}")

if st.session_state.ocr_result:
    ocr_data = st.session_state.ocr_result
    st.subheader("2. Review & Edit Extracted Fields")

    validation = ocr_data.get("validation", {})
    if validation.get("errors"):
        st.error("Required fields missing: " + ", ".join(validation["errors"]))
    if validation.get("warnings"):
        st.warning("Warnings: " + ", ".join(validation["warnings"]))

    edited_fields: List[Dict] = []

    with st.form("edit_form"):
        cols = st.columns(2)
        for idx, field in enumerate(ocr_data["fields"]):
            col = cols[idx % 2]
            with col:
                value = st.session_state.edited_fields.get(field["id"], field.get("text", ""))
                new_value = st.text_input(
                    label=field.get("name", field["id"]),
                    value=value,
                    key=f"field_{field['id']}",
                )
                updated_field = dict(field)
                updated_field["text"] = new_value
                edited_fields.append(updated_field)
        submitted = st.form_submit_button("✅ Validate & Save", type="primary")

    if submitted:
        payload = {
            "template_id": ocr_data["template_id"],
            "form_name": ocr_data.get("form_name", form_name),
            "image_path": ocr_data["image_path"],
            "fields": edited_fields,
        }
        with st.spinner("Saving submission and generating PDF..."):
            try:
                response = submit_form(backend_url, payload)
                st.session_state.last_submission = response
                st.success(f"Submission saved (ID: {response['submission_id']}).")
            except Exception as exc:
                st.error(f"Submission failed: {exc}")

if st.session_state.last_submission:
    submission = st.session_state.last_submission
    st.subheader("3. Download Filled PDF")

    download_url = submission.get("download_url")
    if download_url:
        try:
            pdf_bytes = download_pdf(backend_url, download_url)
            st.download_button(
                label="⬇️ Download Filled PDF",
                data=BytesIO(pdf_bytes),
                file_name="filled_form.pdf",
                mime="application/pdf",
            )
        except Exception as exc:
            st.error(f"Failed to download PDF: {exc}")

    with st.expander("Validation details", expanded=False):
        st.json(submission.get("validation", {}))

    with st.expander("Raw payload", expanded=False):
        st.json(st.session_state.ocr_result)
