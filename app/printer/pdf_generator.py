"""Generate PDFs by overlaying text on template images."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List

from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.utils import get_logger

logger = get_logger(__name__)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_PATH = FONT_DIR / "NotoSansDevanagari-Regular.ttf"
FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "unhinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
)
FONT_NAME = "NotoSansDevanagari"


def _ensure_font():
    if not FONT_PATH.exists():
        FONT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading Noto Sans Devanagari font")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def _px_to_pt(px: float, dpi: int = 300) -> float:
    return px * 72.0 / dpi


def _apply_style(value: str, style) -> str:
    if isinstance(style, str) and style.lower() == "uppercase":
        return value.upper()
    if isinstance(style, dict) and style.get("uppercase"):
        return value.upper()
    return value


def _draw_field(canv: canvas.Canvas, field: Dict, page_height_pt: float, dpi: int):
    bbox = field["bbox_px"]
    x_pt = _px_to_pt(bbox[0], dpi)
    y_pt = page_height_pt - _px_to_pt(bbox[1] + bbox[3], dpi)
    height_pt = _px_to_pt(bbox[3], dpi)
    width_pt = _px_to_pt(bbox[2], dpi)

    font_size = max(8, min(18, height_pt * 0.8))
    canv.setFont(FONT_NAME, font_size)

    value = _apply_style(str(field["value"]), field.get("style"))
    align = "left"
    if isinstance(field.get("style"), dict):
        align = field["style"].get("align", "left")

    if align == "center":
        text_width = canv.stringWidth(value, FONT_NAME, font_size)
        start_x = x_pt + max(0, (width_pt - text_width) / 2)
    elif align == "right":
        text_width = canv.stringWidth(value, FONT_NAME, font_size)
        start_x = x_pt + max(0, width_pt - text_width)
    else:
        start_x = x_pt

    canv.drawString(start_x, y_pt + height_pt * 0.15, value)


def create_filled_pdf(
    template_image: str,
    fields: List[Dict],
    output_path: str,
    dpi: int = 300,
) -> str:
    """
    Overlay normalized field values onto the template image.

    Args:
        template_image: Background image path.
        fields: Output of prepare_pdf_fields.
        output_path: Destination PDF.
        dpi: Template DPI (default 300).
    """
    if not fields:
        raise ValueError("No fields provided for PDF generation")

    _ensure_font()
    pil_image = Image.open(template_image)
    width_px, height_px = pil_image.size
    width_pt = _px_to_pt(width_px, dpi)
    height_pt = _px_to_pt(height_px, dpi)

    canv = canvas.Canvas(output_path, pagesize=(width_pt, height_pt))
    canv.drawImage(
        template_image,
        0,
        0,
        width=width_pt,
        height=height_pt,
        preserveAspectRatio=True,
        mask="auto",
    )

    for field in fields:
        _draw_field(canv, field, height_pt, dpi)

    canv.save()
    logger.info("Saved PDF to %s", output_path)
    return output_path


__all__ = ["create_filled_pdf"]

