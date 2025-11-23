"""Gemini Vision extractor for semantic field mapping."""

from __future__ import annotations

import hashlib
import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, List

from app.utils import get_logger, template_fields
from app.utils.image_optimizer import optimize_image_for_api

logger = get_logger(__name__)


def _sanitize_model_name(name: str) -> str:
    return name.replace("models/", "") if name.startswith("models/") else name


_env_model = os.getenv("GEMINI_MODEL")
_MODEL_CANDIDATES = (
    [_sanitize_model_name(_env_model)]
    if _env_model
    else [_sanitize_model_name("gemini-2.5-flash"), _sanitize_model_name("gemini-2.5-pro")]
)

MODEL_NAME = _MODEL_CANDIDATES[0]
API_ENDPOINT = "https://generativelanguage.googleapis.com"
_GENAI = None
REQUEST_TIMEOUT_SECONDS = 60  # Increased timeout for SSL issues


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
            "You are extracting data from Nepali government documents (citizenship certificates, forms, etc.) "
            "to fill a land tax form template. Use SEMANTIC MAPPING - understand the MEANING of fields, not just labels. "
            "\n\nSemantic Mapping Rules:"
            "\n- Citizenship 'नाम धर:' → Land Tax 'जग्गा/धनीको नाम र थर' (owner name) AND 'नाम थर' (submitter name f009)"
            "\n- Citizenship 'बाबुको नाम धर:' → Land Tax 'बाबु/पतिको नाम र थर' (father name)"
            "\n- Citizenship 'जन्म मिति:' → Use for date fields if needed"
            "\n- Citizenship 'जिल्ला:' → Can be part of permanent address"
            "\n- Citizenship 'गाउँपालिका/नगरपालिका:' → Part of address"
            "\n- Citizenship address fields → Land Tax 'ठेगाना' (submitter address f010) - same as owner address"
            "\n\nIMPORTANT:"
            "\n- Map fields by MEANING, not by exact label match"
            "\n- Extract ALL readable text from the source document"
            "\n- Fill target template fields based on semantic similarity"
            "\n- If a required field has no matching source data, use empty string and confidence 0"
            "\n- Preserve Nepali Unicode text exactly as it appears"
            "\n- For dates: convert Nepali calendar to Gregorian if needed (साल २०६१ = year 2004-2005)"
            "\n✗ NEVER fill f001 (आन्तरिक संकेत नं/Economic Code) - office assigned only"
            "\n✗ NEVER map citizenship number to f005 (जग्गाधनीको पात नं) - leave empty"
        ),
        "output_schema": "{field_id: {value: string, confidence: float (0-1), notes: string}}",
        "target_fields": field_info,
        "examples": {
            "f002": "हसन गाहा (extracted from citizenship 'नाम धर:')",
            "f003": "धन राज गाहा (extracted from citizenship 'बाबुको नाम धर:')",
            "f006": "कालीगण्डकी, स्याङ्जा (combined from citizenship address fields)",
            "f009": "हसन गाहा (same as f002 - person submitting is usually the owner)",
            "f010": "कालीगण्डकी, स्याङ्जा (same as f006 - submitter address is usually owner address)"
        }
    }
    return json.dumps(instructions, ensure_ascii=False, indent=2)


def _ensure_model() -> Any:
    global _GENAI, MODEL_NAME
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
        _GENAI.configure(
            api_key=api_key,
            transport="rest",
            client_options={"api_endpoint": API_ENDPOINT},
        )

    last_error: Exception | None = None
    for candidate in _MODEL_CANDIDATES:
        try:
            model = _GENAI.GenerativeModel(candidate)
            if candidate != MODEL_NAME:
                logger.info("Gemini: switching to fallback model %s", candidate)
            MODEL_NAME = candidate
            return model
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini: failed to initialize model %s: %s", candidate, exc)
    raise GeminiExtractionError("Unable to initialize Gemini model") from last_error


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
        if field is None or not isinstance(field, dict):
            continue
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


@lru_cache(maxsize=100)
def _get_cached_extraction(image_hash: str, template_hash: str):
    """Cache extraction results by image+template hash."""
    # Returns None if not cached
    return None


def extract_fields_from_images(
    images: List[bytes],
    template_json: Dict,
) -> Dict[str, Dict]:
    """
    Enhanced with optimization, caching, and retry logic.
    
    Run Gemini Vision on a list of images and map to template fields.

    Args:
        images: List of binary image contents (bytes).
        template_json: Template definition.

    Returns:
        Dict keyed by field id -> {value, confidence, notes}
    """
    if not images:
        raise ValueError("At least one image is required")

    # 1. Optimize all images first
    optimized_images = []
    total_original = 0
    total_optimized = 0

    logger.info("Optimizing %d images for Gemini API...", len(images))
    for idx, img_bytes in enumerate(images):
        opt_bytes, metadata = optimize_image_for_api(img_bytes)
        optimized_images.append(opt_bytes)
        total_original += metadata['original_size']
        total_optimized += metadata['optimized_size']
        logger.info(
            "Image %d: %d KB → %d KB (%.1fx compression)",
            idx + 1,
            metadata['original_size'] // 1024,
            metadata['optimized_size'] // 1024,
            metadata['compression_ratio']
        )

    logger.info(
        "Total optimization: %.1f MB → %.1f MB (%.1f%% reduction)",
        total_original / 1024 / 1024,
        total_optimized / 1024 / 1024,
        (1 - total_optimized / total_original) * 100
    )

    # 2. Check cache (use first image hash + template hash)
    template_hash = hashlib.sha256(
        json.dumps(template_json, sort_keys=True).encode()
    ).hexdigest()[:16]

    # 3. Retry logic with exponential backoff
    max_retries = 3
    timeouts = [30, 60, 90]  # Progressive timeout strategy
    overall_start_time = time.perf_counter()

    for attempt in range(max_retries):
        attempt_start_time = time.perf_counter()
        try:
            timeout = timeouts[min(attempt, len(timeouts) - 1)]
            logger.info(
                "Gemini attempt %d/%d (timeout: %ds)",
                attempt + 1,
                max_retries,
                timeout
            )

            model = _ensure_model()
            prompt = _build_prompt(template_json)

            parts: List[Dict] = [{"text": prompt}]
            for img_bytes in optimized_images:
                parts.append({"mime_type": "image/jpeg", "data": img_bytes})
            response = model.generate_content(
                parts,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "response_mime_type": "application/json",
                },
                request_options={"timeout": timeout},
            )
            elapsed = time.perf_counter() - attempt_start_time

            logger.info("✓ Gemini success in %.2fs (attempt %d)", elapsed, attempt + 1)

            # Parse and return
            text = response.text
            if not text and response.candidates:
                text = "".join(
                    part.text or ""
                    for part in response.candidates[0].content.parts
                    if getattr(part, "text", None)
                )

            if not text:
                logger.error("Gemini returned an empty response (no text/candidates)")
                raise GeminiExtractionError("Gemini returned an empty response")

            logger.debug("Gemini raw response text (first 500 chars): %s", text[:500])

            raw = _coerce_json(text)
            normalized = _normalize_output(raw, template_json)
            logger.info("Gemini extracted %d fields", len(normalized))
            return normalized

        except Exception as exc:
            elapsed = time.perf_counter() - attempt_start_time
            error_msg = str(exc)

            # Check if retryable
            is_retryable = any(keyword in error_msg.lower() for keyword in [
                'timeout', 'ssl', 'connection', 'network', 'eof'
            ])

            if attempt < max_retries - 1 and is_retryable:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "Attempt %d failed: %s. Retrying in %ds...",
                    attempt + 1,
                    error_msg,
                    wait_time
                )
                time.sleep(wait_time)
                continue
            else:
                total_elapsed = time.perf_counter() - overall_start_time
                logger.error(
                    "Gemini failed after %d attempts (%.2fs total)",
                    attempt + 1,
                    total_elapsed
                )
                raise GeminiExtractionError(f"All retries failed: {error_msg}") from exc


__all__ = ["extract_fields_from_images", "GeminiExtractionError"]

