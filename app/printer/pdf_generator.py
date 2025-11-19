"""Generate PDFs by overlaying text on template images."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Dict, List

from PIL import Image
from reportlab.lib import colors
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


def _apply_style(value: str, style) -> str:
    if isinstance(style, str) and style.lower() == "uppercase":
        return value.upper()
    if isinstance(style, dict) and style.get("uppercase"):
        return value.upper()
    return value


def _draw_field(canv: canvas.Canvas, field: Dict, bg_height: int, font_name: str):
    fid = field.get("id", "unknown")
    value = str(field.get("value", "")).strip()
    bbox = field.get("bbox_px")

    if not bbox or len(bbox) != 4:
        print(f"⚠️  Field {fid}: Invalid bbox {bbox}")
        return

    if not value:
        print(f"⚠️  Field {fid}: Empty value")
        return

    x, y, w, h = bbox
    font_size = max(8, min(int(h * 0.6), 16))
    pdf_y = bg_height - y - h
    text_y = pdf_y + (h - font_size) / 2

    print(f"Field {fid}:")
    print(f"  Value: {value}")
    print(f"  BBox: x={x}, y={y}, w={w}, h={h}")
    print(f"  PDF coords: x={x}, y={pdf_y}")
    print(f"  Font size: {font_size}")

    value = _apply_style(value, field.get("style"))

    canv.setFont(font_name, font_size)
    canv.setFillColor(colors.black)
    canv.drawString(x, text_y, value)


def create_filled_pdf(
    template_image: str,
    fields: List[Dict],
    output_path: str,
) -> str:
    """Overlay normalized field values onto the template image."""
    if not fields:
        raise ValueError("No fields provided for PDF generation")

    pil_image = Image.open(template_image)
    width_px, height_px = pil_image.size

    print("\n" + "=" * 60)
    print("PDF Generation Debug Info")
    print(f"Background: {template_image}")
    print(f"Background size: {width_px}x{height_px}px")
    print(f"Number of fields: {len(fields)}")
    print("=" * 60 + "\n")

    canv = canvas.Canvas(output_path, pagesize=(width_px, height_px))
    canv.drawImage(template_image, 0, 0, width=width_px, height=height_px)

    nep_font_path = Path(__file__).parent / "fonts" / "NotoSansDevanagari-Regular.ttf"
    if nep_font_path.exists():
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(nep_font_path)))
        font_name = FONT_NAME
    else:
        print(f"WARNING: Nepali font not found at {nep_font_path}")
        font_name = "Helvetica"

    for field in fields:
        _draw_field(canv, field, height_px, font_name)

    canv.save()
    print("=" * 60)
    print(f"PDF saved: {output_path}")
    print("=" * 60 + "\n")
    return output_path


__all__ = ["create_filled_pdf"]

