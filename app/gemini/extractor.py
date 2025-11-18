"""Gemini Vision extractor for semantic field mapping."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from app.utils import get_logger, template_fields

logger = get_logger(__name__)

_raw_model = os.getenv("GEMINI_MODEL") or "models/gemini-1.5-flash"
MODEL_NAME = _raw_model if _raw_model.startswith("models/") else f"models/{_raw_model}"
_GENAI = None


class GeminiExtractionError(RuntimeError):
    """Raised when Gemini Vision cannot complete the request."""


def _build_prompt(template_json: Dict) -> str:
    field_info = []
    for field in template_fields(template_json):
        if not isinstance(field, dict):
            continue
        ocr_cfg = field.get("ocr") or {}
        if not isinstance(ocr_cfg, dict):
            ocr_cfg = {}
        field_info.append(
            {
                "id": field.get("id"),
                "name": field.get("name") or field.get("label"),
                "label": field.get("label"),
                "meaning": field.get("desc"),
                "type": field.get("type"),
                "language_hint": ocr_cfg.get("lang"),
            }
        )

    instructions = {
        "task": (
            "Read all attached Nepali government form images. "
            "Interpret fields by meaning (semantic mapping). "
            "Fill the provided template fields only. "
            "Do not invent data. If a value is missing, use an empty string and confidence 0."
        ),
        "output_schema": "{field_id: {value: string, confidence: float (0-1), notes: string}}",
        "field_list": field_info,
    }
    return json.dumps(instructions, ensure_ascii=False, indent=2)


def _ensure_model() -> Any:
    global _GENAI
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiExtractionError("GEMINI_API_KEY is not set")
    if _GENAI is None:
        try:
            import google.generativeai as genai_mod  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - import guard
            raise GeminiExtractionError(
                "google-generativeai is not installed. "
                "Add it via pip install google-generativeai."
            ) from exc
        _GENAI = genai_mod
    _GENAI.configure(api_key=api_key)
    return _GENAI.GenerativeModel(MODEL_NAME)


def _coerce_json(payload: str) -> Dict:
    payload = payload.strip()
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        # Try to salvage by locating the outermost braces.
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = payload[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        raise


def _normalize_output(raw: Dict, template_json: Dict) -> Dict[str, Dict]:
    normalized: Dict[str, Dict] = {}
    for field in template_fields(template_json):
        fid = field.get("id")
        if not fid:
            continue
        entry = raw.get(fid) if isinstance(raw, dict) else None
        if isinstance(entry, dict):
            value = entry.get("value", "")
            confidence = entry.get("confidence", entry.get("score", 0))
            notes = entry.get("notes") or entry.get("explanation")
        else:
            value = entry if isinstance(entry, str) else ""
            confidence = 0
            notes = None

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        normalized[fid] = {
            "value": value.strip(),
            "confidence": max(0.0, min(1.0, confidence)),
            "notes": notes or "",
        }
    return normalized


def extract_fields_from_images(
    images: List[bytes],
    template_json: Dict,
) -> Dict[str, Dict]:
    """
    Run Gemini Vision on a list of images and map to template fields.

    Args:
        images: List of binary image contents (bytes).
        template_json: Template definition.

    Returns:
        Dict keyed by field id -> {value, confidence, notes}
    """
    if not images:
        raise ValueError("At least one image is required for extraction")

    model = _ensure_model()
    prompt = _build_prompt(template_json)

    parts: List[Dict] = [{"text": prompt}]
    for image_bytes in images:
        parts.append({"mime_type": "image/jpeg", "data": image_bytes})

    try:
        response = model.generate_content(
            parts,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "response_mime_type": "application/json",
            },
        )
    except Exception as exc:  # pragma: no cover - network failure
        raise GeminiExtractionError(str(exc)) from exc

    text = response.text
    if not text and response.candidates:
        text = "".join(
            part.text or ""
            for part in response.candidates[0].content.parts
            if getattr(part, "text", None)
        )

    if not text:
        raise GeminiExtractionError("Gemini returned an empty response")

    try:
        raw = _coerce_json(text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini response: %s", text)
        raise GeminiExtractionError("Unable to parse Gemini JSON output") from exc

    normalized = _normalize_output(raw, template_json)
    logger.info("Gemini extracted %d fields", len(normalized))
    return normalized


__all__ = ["extract_fields_from_images", "GeminiExtractionError"]

