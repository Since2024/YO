"""Normalize Gemini output for downstream PDF filling."""

from __future__ import annotations

import re
from typing import Dict, List

from app.utils import template_fields

NEPALI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _normalize_digits(value: str) -> str:
    return value.translate(NEPALI_DIGITS)


def _normalize_date(value: str) -> str:
    clean = _normalize_digits(value).replace(".", "-").replace("/", "-")
    clean = re.sub(r"\s+", "", clean)
    # Accept YYYY-MM-DD or DD-MM-YYYY patterns.
    parts = clean.split("-")
    if len(parts) != 3:
        return value.strip()
    if len(parts[0]) == 4:
        year, month, day = parts
    else:
        day, month, year = parts
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return value.strip()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", _normalize_digits(value))
    if digits.startswith("977") and len(digits) > 10:
        digits = digits[-10:]
    return digits


def _normalize_default(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_value(field: Dict, value: str) -> str:
    ftype = (field.get("type") or "").lower()
    if not value:
        return ""
    if ftype in {"date", "text_date"} or field.get("validate", {}).get("type") == "date":
        return _normalize_date(value)
    if "phone" in ftype or field.get("validate", {}).get("type") == "phone":
        return _normalize_phone(value)
    if ftype in {"number", "box_grid"} or field.get("validate", {}).get("type") == "number":
        return _normalize_digits(value).replace(" ", "")
    return _normalize_default(value)


def prepare_pdf_fields(gemini_output: Dict[str, Dict], template_json: Dict) -> List[Dict]:
    """
    Merge Gemini output with template metadata for PDF generation.

    Returns:
        List of dicts with keys: id, name, value, confidence, bbox_px, page, style
    """
    prepared: List[Dict] = []
    for field in template_fields(template_json):
        fid = field.get("id")
        bbox = (field.get("bbox") or {}).get("px")
        if not fid or not bbox or len(bbox) != 4:
            continue

        entry = gemini_output.get(fid, {})
        raw_value = entry.get("value", "")
        normalized = _normalize_value(field, raw_value)
        if normalized == "":
            continue

        try:
            confidence = float(entry.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        prepared.append(
            {
                "id": fid,
                "name": field.get("name", fid),
                "value": normalized,
                "confidence": max(0.0, min(1.0, confidence)),
                "bbox_px": bbox,
                "page": field.get("page", 1),
                "style": field.get("style", "normal"),
            }
        )
    return prepared


__all__ = ["prepare_pdf_fields"]

