"""PDF generation module using ReportLab with Nepali font support."""

import os
import urllib.request
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from utils.logger import get_logger

logger = get_logger(__name__)

# Font paths - try system fonts first
FONT_PATHS = [
    "/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Regular.ttf",
    "fonts/NotoSansDevanagari-Regular.ttf",  # Local fallback
]

# Font download URL (Google Fonts CDN)
FONT_DOWNLOAD_URL = "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Regular.ttf"

# Register Nepali font if available
NEPALI_FONT_REGISTERED = False
NEPALI_FONT_NAME = "NotoSansDevanagari"


def _download_font(font_dir: Path) -> Optional[Path]:
    """Download Noto Sans Devanagari font if not found locally."""
    try:
        font_dir.mkdir(parents=True, exist_ok=True)
        font_path = font_dir / "NotoSansDevanagari-Regular.ttf"
        
        if font_path.exists():
            return font_path
        
        logger.info(f"Downloading Noto Sans Devanagari font to {font_path}...")
        urllib.request.urlretrieve(FONT_DOWNLOAD_URL, font_path)
        logger.info(f"✅ Font downloaded successfully")
        return font_path
    except Exception as e:
        logger.warning(f"Failed to download font: {e}")
        return None


def _register_nepali_font():
    """Register Noto Sans Devanagari font with ReportLab."""
    global NEPALI_FONT_REGISTERED
    
    if NEPALI_FONT_REGISTERED:
        return True
    
    # Try system fonts first
    for font_path in FONT_PATHS:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(NEPALI_FONT_NAME, font_path))
                logger.info(f"✅ Registered Nepali font: {font_path}")
                NEPALI_FONT_REGISTERED = True
                return True
            except Exception as e:
                logger.warning(f"Failed to register font {font_path}: {e}")
                continue
    
    # Try downloading font
    font_dir = Path("fonts")
    downloaded_font = _download_font(font_dir)
    if downloaded_font and downloaded_font.exists():
        try:
            pdfmetrics.registerFont(TTFont(NEPALI_FONT_NAME, str(downloaded_font)))
            logger.info(f"✅ Registered downloaded Nepali font: {downloaded_font}")
            NEPALI_FONT_REGISTERED = True
            return True
        except Exception as e:
            logger.warning(f"Failed to register downloaded font: {e}")
    
    logger.warning("⚠️ Nepali font not found. Nepali text may not render correctly.")
    return False


# Register font on module import
_register_nepali_font()


class PDFGenerator:
    """Generates filled PDF forms using ReportLab with proper Nepali font support."""
    
    def __init__(self, dpi: int = 300):
        """
        Initialize PDF generator.
        
        Args:
            dpi: Output resolution (default 300 for print quality)
        """
        self.page_width, self.page_height = A4
        self.dpi = dpi
        self.points_per_inch = 72
        logger.info(f"PDF Generator initialized (DPI: {dpi})")
    
    def _convert_px_to_points(self, x_px: float, y_px: float, 
                             image_width_px: int, image_height_px: int,
                             template_dpi: int = 300) -> tuple:
        """
        Convert pixel coordinates to PDF points with proper DPI handling.
        
        Args:
            x_px: X coordinate in pixels
            y_px: Y coordinate in pixels (top-left origin)
            image_width_px: Image width in pixels
            image_height_px: Image height in pixels
            template_dpi: DPI of the template image
            
        Returns:
            Tuple of (x_points, y_points) where y is from bottom-left
        """
        # Convert pixels to inches
        x_inch = x_px / template_dpi
        y_inch = y_px / template_dpi
        
        # Convert inches to points
        x_pt = x_inch * self.points_per_inch
        y_pt = y_inch * self.points_per_inch
        
        # Convert Y from top-left to bottom-left origin
        image_height_inch = image_height_px / template_dpi
        image_height_pt = image_height_inch * self.points_per_inch
        y_pt = image_height_pt - y_pt
        
        return (x_pt, y_pt)
    
    def _wrap_text(self, text: str, font_name: str, font_size: float, max_width_pt: float) -> List[str]:
        """
        Wrap text to fit within maximum width.
        
        Args:
            text: Text to wrap
            font_name: Font name
            font_size: Font size in points
            max_width_pt: Maximum width in points
            
        Returns:
            List of text lines
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width = stringWidth(test_line, font_name, font_size)
            
            if width <= max_width_pt:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]
    
    def create_filled_pdf(self, template_image: str, fields: List[Dict[str, Any]], 
                         output_path: str, dpi: int = 300) -> None:
        """
        Create filled PDF with embedded Nepali font, proper coordinate conversion, 
        and support for box_grid and table rendering.
        
        Args:
            template_image: Path to template image
            fields: List of field data with text, bbox, and rendering metadata
            output_path: Path for output PDF
            dpi: DPI of template (default 300)
        """
        logger.info(f"Creating filled PDF: {output_path}")
        
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Read template image
            img = cv2.imread(template_image)
            if img is None:
                raise ValueError(f"Failed to read template image: {template_image}")
            
            img_height, img_width = img.shape[:2]
            
            # Get paper size from template metadata or default to A4
            paper_size = A4  # Default to A4
            
            # Create PDF canvas
            c = canvas.Canvas(output_path, pagesize=paper_size)
            
            # Draw background image (scaled to fit page)
            img_aspect = img_width / img_height
            page_aspect = self.page_width / self.page_height
            
            if img_aspect > page_aspect:
                draw_width = self.page_width
                draw_height = self.page_width / img_aspect
                x_offset = 0
                y_offset = (self.page_height - draw_height) / 2
            else:
                draw_height = self.page_height
                draw_width = self.page_height * img_aspect
                x_offset = (self.page_width - draw_width) / 2
                y_offset = 0
            
            # Draw template image
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            img_path_temp = str(Path(output_path).with_suffix('.temp_img.jpg'))
            pil_img.save(img_path_temp, 'JPEG', quality=95)
            c.drawImage(img_path_temp, x_offset, y_offset, width=draw_width, height=draw_height)
            
            # Calculate scaling factors
            scale_x = draw_width / img_width
            scale_y = draw_height / img_height
            
            # Use Nepali font if available
            font_name = NEPALI_FONT_NAME if NEPALI_FONT_REGISTERED else "Helvetica"
            
            # Draw filled fields
            for field in fields:
                text = field.get('text', '').strip()
                bbox = field.get('bbox', {})
                field_type = field.get('type', 'text_line')
                rendering = field.get('rendering', 'text')
                
                # Skip empty fields and signature boxes (unless image provided)
                if field_type == 'signature_box':
                    # Check if signature image is provided
                    if 'signature_image' in field:
                        sig_img_path = field['signature_image']
                        if os.path.exists(sig_img_path):
                            x_px, y_px, width_px, height_px = bbox.get('px', [0, 0, 100, 50])
                            x_pt = x_px * scale_x + x_offset
                            y_pt = self.page_height - (y_px * scale_y + y_offset + height_px * scale_y)
                            c.drawImage(sig_img_path, x_pt, y_pt, 
                                      width=width_px * scale_x, height=height_px * scale_y)
                    continue
                
                if not text or not bbox or 'px' not in bbox:
                    continue
                
                x_px, y_px, width_px, height_px = bbox['px']
                
                # Scale coordinates
                x_pt = x_px * scale_x + x_offset
                y_pt = self.page_height - (y_px * scale_y + y_offset + height_px * scale_y)
                width_pt = width_px * scale_x
                height_pt = height_px * scale_y
                
                # Draw white rectangle to mask existing text
                c.setFillColorRGB(1, 1, 1)
                c.rect(x_pt, y_pt, width_pt, height_pt, fill=1, stroke=0)
                
                # Render based on type
                if rendering == 'box_grid':
                    self._render_box_grid(c, field, x_pt, y_pt, width_pt, height_pt, font_name)
                elif rendering == 'table':
                    self._render_table(c, field, x_pt, y_pt, width_pt, height_pt, font_name)
                else:
                    self._render_text(c, text, x_pt, y_pt, width_pt, height_pt, font_name)
            
            # Save PDF
            c.save()
            
            # Clean up temp image
            if os.path.exists(img_path_temp):
                os.remove(img_path_temp)
            
            logger.info(f"✅ Filled PDF created: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create filled PDF: {e}")
            raise
    
    def _render_text(self, c: canvas.Canvas, text: str, x_pt: float, y_pt: float,
                    width_pt: float, height_pt: float, font_name: str) -> None:
        """Render regular text field with blue color for filled text."""
        font_size = max(8, min(height_pt * 0.7, 14))
        lines = self._wrap_text(text, font_name, font_size, width_pt - 4)
        
        # Use blue color for filled text to distinguish from printed text
        c.setFont(font_name, font_size)
        c.setFillColorRGB(0, 0, 0.8)  # Blue
        
        line_height = font_size * 1.2
        start_y = y_pt + height_pt - (height_pt - (len(lines) * line_height)) / 2
        
        for i, line in enumerate(lines):
            if i * line_height > height_pt:
                break
            c.drawString(x_pt + 2, start_y - (i * line_height), line)
    
    def _render_box_grid(self, c: canvas.Canvas, field: Dict[str, Any], 
                        x_pt: float, y_pt: float, width_pt: float, height_pt: float,
                        font_name: str) -> None:
        """Render box_grid field (one character per cell)."""
        text = field.get('text', '').strip()
        grid = field.get('grid', {})
        num_boxes = grid.get('boxes', len(text))
        spacing = grid.get('spacing', width_pt / num_boxes)
        box_width = grid.get('box_width', width_pt / num_boxes)
        
        # Calculate box dimensions
        box_width_pt = (box_width / 300) * 72  # Convert from pixels to points (assuming 300 DPI)
        box_height_pt = height_pt
        spacing_pt = (spacing / 300) * 72
        
        font_size = max(8, min(box_height_pt * 0.7, 12))
        c.setFont(font_name, font_size)
        c.setFillColorRGB(0, 0, 0.8)  # Blue for filled text
        
        # Draw one character per box
        for i, char in enumerate(text[:num_boxes]):
            box_x = x_pt + i * (box_width_pt + spacing_pt)
            char_x = box_x + (box_width_pt - stringWidth(char, font_name, font_size)) / 2
            char_y = y_pt + (box_height_pt - font_size) / 2
            c.drawString(char_x, char_y, char)
    
    def _render_table(self, c: canvas.Canvas, field: Dict[str, Any],
                     x_pt: float, y_pt: float, width_pt: float, height_pt: float,
                     font_name: str) -> None:
        """Render table field with rows."""
        table_config = field.get('table', {})
        rows = field.get('rows', [])
        
        if not rows:
            # Fallback to text rendering
            self._render_text(c, field.get('text', ''), x_pt, y_pt, width_pt, height_pt, font_name)
            return
        
        font_size = max(8, min(height_pt / len(rows) * 0.7, 12))
        c.setFont(font_name, font_size)
        c.setFillColorRGB(0, 0, 0.8)  # Blue
        
        row_height = height_pt / len(rows)
        for i, row in enumerate(rows):
            row_text = ' '.join(str(cell) for cell in row) if isinstance(row, list) else str(row)
            row_y = y_pt + height_pt - (i + 1) * row_height + (row_height - font_size) / 2
            c.drawString(x_pt + 2, row_y, row_text[:int(width_pt / font_size * 0.8)])  # Truncate if too long
    
    def create_filled_pdf_from_image(self, template_image_path: str, 
                                     extracted_data: List[Dict[str, Any]], 
                                     output_path: str) -> None:
        """
        Create a filled PDF using ReportLab with proper Nepali font and coordinates.
        
        Args:
            template_image_path: Path to template image (background)
            extracted_data: List of field data with text and bbox
            output_path: Path for output PDF
        """
        logger.info(f"Creating filled PDF from template image: {template_image_path}")
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Read template image to get dimensions
            img = cv2.imread(template_image_path)
            if img is None:
                raise ValueError(f"Failed to read template image: {template_image_path}")
            
            img_height, img_width = img.shape[:2]
            
            # Get template DPI from metadata or assume 300
            template_dpi = 300  # Default assumption
            
            # Create PDF canvas
            c = canvas.Canvas(output_path, pagesize=A4)
            
            # Draw background image (scaled to A4)
            # Calculate scaling to fit A4 while maintaining aspect ratio
            img_aspect = img_width / img_height
            page_aspect = self.page_width / self.page_height
            
            if img_aspect > page_aspect:
                # Image is wider - fit to width
                draw_width = self.page_width
                draw_height = self.page_width / img_aspect
                x_offset = 0
                y_offset = (self.page_height - draw_height) / 2
            else:
                # Image is taller - fit to height
                draw_height = self.page_height
                draw_width = self.page_height * img_aspect
                x_offset = (self.page_width - draw_width) / 2
                y_offset = 0
            
            # Draw image
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            img_path_temp = str(Path(output_path).with_suffix('.temp_img.jpg'))
            pil_img.save(img_path_temp, 'JPEG', quality=95)
            c.drawImage(img_path_temp, x_offset, y_offset, width=draw_width, height=draw_height)
            
            # Calculate scaling factors
            scale_x = draw_width / img_width
            scale_y = draw_height / img_height
            
            # Use Nepali font if available, fallback to Helvetica
            font_name = NEPALI_FONT_NAME if NEPALI_FONT_REGISTERED else "Helvetica"
            
            # Draw text fields
            for field_data in extracted_data:
                text = field_data.get('text', '').strip()
                bbox = field_data.get('bbox', {})
                field_type = field_data.get('type', 'text_line')
                
                # Skip signature fields
                if field_type == 'signature_box' or text == '[SIGNATURE]' or not text:
                    continue
                
                if not bbox or 'px' not in bbox:
                    continue
                
                # Get bbox coordinates
                x_px, y_px, width_px, height_px = bbox['px']
                
                # Scale coordinates to match drawn image
                x_scaled = x_px * scale_x + x_offset
                y_scaled = y_px * scale_y + y_offset
                width_scaled = width_px * scale_x
                height_scaled = height_px * scale_y
                
                # Convert to points (Y is already from bottom in ReportLab)
                # But we need to account for the image offset
                x_pt = x_scaled
                y_pt = self.page_height - (y_scaled + height_scaled)  # Bottom of bbox
                
                # Draw white rectangle to mask existing text
                c.setFillColorRGB(1, 1, 1)  # White
                c.rect(x_pt, y_pt, width_scaled, height_scaled, fill=1, stroke=0)
                
                # Calculate font size based on bbox height
                font_size = max(8, min(height_scaled * 0.7, 14))  # Reasonable range
                
                # Wrap text if needed
                lines = self._wrap_text(text, font_name, font_size, width_scaled - 4)
                
                # Set font and color
                c.setFont(font_name, font_size)
                c.setFillColorRGB(0, 0, 0)  # Black
                
                # Draw text lines
                line_height = font_size * 1.2
                start_y = y_pt + height_scaled - (height_scaled - (len(lines) * line_height)) / 2
                
                for i, line in enumerate(lines):
                    if i * line_height > height_scaled:
                        break
                    c.drawString(x_pt + 2, start_y - (i * line_height), line)
            
            # Save PDF
            c.save()
            
            # Clean up temp image
            if os.path.exists(img_path_temp):
                os.remove(img_path_temp)
            
            logger.info(f"✅ Filled PDF created successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create filled PDF: {e}")
            raise
    
    def create_pdf_with_reportlab(self, template_data: Dict[str, Any],
                                 extracted_data: List[Dict[str, Any]],
                                 output_path: str) -> None:
        """
        Create a PDF using ReportLab with text overlays (alternative method).
        
        Args:
            template_data: Template configuration
            extracted_data: List of field data
            output_path: Path for output PDF
        """
        logger.info(f"Creating PDF with ReportLab: {output_path}")
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Get template metadata
            metadata = template_data.get('metadata', {})
            image_dims = metadata.get('image_dimensions_px', {})
            template_dpi = metadata.get('dpi', 300)
            
            img_width = image_dims.get('width', 847)
            img_height = image_dims.get('height', 1197)
            
            # Create PDF canvas
            c = canvas.Canvas(output_path, pagesize=A4)
            
            # Use Nepali font if available
            font_name = NEPALI_FONT_NAME if NEPALI_FONT_REGISTERED else "Helvetica"
            
            # Add fields to PDF
            for field_data in extracted_data:
                text = field_data.get('text', '').strip()
                bbox = field_data.get('bbox', {})
                field_type = field_data.get('type', 'text_line')
                
                if not text or field_type == 'signature_box' or not bbox or 'px' not in bbox:
                    continue
                
                # Get coordinates in pixels
                x_px, y_px, width_px, height_px = bbox['px']
                
                # Convert to points using proper DPI
                x_pt, y_pt = self._convert_px_to_points(
                    x_px, y_px, img_width, img_height, template_dpi
                )
                
                # Get width and height in points
                width_pt = (width_px / template_dpi) * self.points_per_inch
                height_pt = (height_px / template_dpi) * self.points_per_inch
                
                # Draw white rectangle to mask existing text
                c.setFillColorRGB(1, 1, 1)
                c.rect(x_pt, y_pt - height_pt, width_pt, height_pt, fill=1, stroke=0)
                
                # Calculate font size
                font_size = max(8, min(height_pt * 0.7, 14))
                
                # Wrap text
                lines = self._wrap_text(text, font_name, font_size, width_pt - 4)
                
                # Set font and draw text
                c.setFont(font_name, font_size)
                c.setFillColorRGB(0, 0, 0)
                
                line_height = font_size * 1.2
                start_y = y_pt - (height_pt - (len(lines) * line_height)) / 2
                
                for i, line in enumerate(lines):
                    if i * line_height > height_pt:
                        break
                    c.drawString(x_pt + 2, start_y - (i * line_height), line)
            
            # Save PDF
            c.save()
            
            logger.info(f"✅ PDF created successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create PDF with ReportLab: {e}")
            raise
    
    def _overlay_text_on_image(self, image: np.ndarray, 
                              extracted_data: List[Dict[str, Any]]) -> np.ndarray:
        """
        Overlay extracted text on image (legacy method - kept for compatibility).
        
        Note: This method doesn't support Nepali fonts properly.
        Use create_filled_pdf_from_image() instead for proper rendering.
        
        Args:
            image: Input image (numpy array)
            extracted_data: List of field data with text and bbox
            
        Returns:
            Image with text overlays
        """
        # Create a copy
        overlay_img = image.copy()
        
        for field_data in extracted_data:
            text = field_data.get('text', '')
            bbox = field_data.get('bbox', {})
            field_type = field_data.get('type', 'text')
            
            # Skip signature fields
            if field_type == 'signature_box' or text == '[SIGNATURE]':
                continue
            
            if not text or not bbox or 'px' not in bbox:
                continue
            
            # Get bbox coordinates
            x, y, width, height = bbox['px']
            
            # Draw white rectangle as background (to cover existing text)
            cv2.rectangle(overlay_img, (x, y), (x + width, y + height), (255, 255, 255), -1)
            
            # Calculate font size based on box height
            font_scale = min(height / 40.0, 1.0)
            thickness = max(1, int(font_scale * 2))
            
            # Put text (Note: OpenCV doesn't support Nepali fonts well)
            cv2.putText(
                overlay_img, text, (x + 2, y + height - 5),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness
            )
        
        return overlay_img
    
    def create_image_overlay(self, template_image_path: str,
                            extracted_data: List[Dict[str, Any]],
                            output_path: str) -> None:
        """
        Create an image with text overlays (useful for debugging).
        
        Args:
            template_image_path: Path to template image
            extracted_data: List of field data
            output_path: Path for output image
        """
        logger.info(f"Creating image overlay: {output_path}")
        
        try:
            # Read template image
            img = cv2.imread(template_image_path)
            if img is None:
                raise ValueError(f"Failed to read template image: {template_image_path}")
            
            # Overlay text
            filled_image = self._overlay_text_on_image(img, extracted_data)
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            cv2.imwrite(output_path, filled_image)
            
            logger.info(f"Image overlay created successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create image overlay: {e}")
            raise
