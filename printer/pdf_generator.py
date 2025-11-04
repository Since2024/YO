"""PDF generation module using ReportLab and OpenCV."""

import os
from typing import Dict, Any, List
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFGenerator:
    """Generates filled PDF forms using ReportLab."""
    
    def __init__(self):
        """Initialize PDF generator."""
        self.page_width, self.page_height = A4
        logger.info("PDF Generator initialized")
    
    def create_filled_pdf_from_image(self, template_image_path: str, 
                                     extracted_data: List[Dict[str, Any]], 
                                     output_path: str) -> None:
        """
        Create a filled PDF by overlaying text on template image.
        
        Args:
            template_image_path: Path to template image (background)
            extracted_data: List of field data with text and bbox
            output_path: Path for output PDF
        """
        logger.info(f"Creating filled PDF from template image: {template_image_path}")
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Read template image
            img = cv2.imread(template_image_path)
            if img is None:
                raise ValueError(f"Failed to read template image: {template_image_path}")
            
            # Overlay text on image
            filled_image = self._overlay_text_on_image(img, extracted_data)
            
            # Convert to RGB (PIL)
            filled_image_rgb = cv2.cvtColor(filled_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(filled_image_rgb)
            
            # Save as PDF
            pil_image.save(output_path, "PDF", resolution=100.0)
            
            logger.info(f"Filled PDF created successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create filled PDF: {e}")
            raise
    
    def create_pdf_with_reportlab(self, template_data: Dict[str, Any],
                                 extracted_data: List[Dict[str, Any]],
                                 output_path: str) -> None:
        """
        Create a PDF using ReportLab with text overlays.
        
        Args:
            template_data: Template configuration
            extracted_data: List of field data
            output_path: Path for output PDF
        """
        logger.info(f"Creating PDF with ReportLab: {output_path}")
        
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create PDF canvas
            c = canvas.Canvas(output_path, pagesize=A4)
            
            # Set default font
            c.setFont("Helvetica", 10)
            
            # Add fields to PDF
            for field_data in extracted_data:
                text = field_data.get('text', '')
                bbox = field_data.get('bbox', {})
                
                if not text or not bbox or 'px' not in bbox:
                    continue
                
                # Get coordinates in pixels
                x_px, y_px, width_px, height_px = bbox['px']
                
                # Convert to mm if available, otherwise use pixel-to-mm conversion
                if 'mm' in bbox:
                    x_mm, y_mm, width_mm, height_mm = bbox['mm']
                else:
                    # Default conversion: assume 3 pixels per mm
                    pixel_to_mm = 0.248
                    x_mm = x_px * pixel_to_mm
                    y_mm = y_px * pixel_to_mm
                
                # Convert mm to points (1mm = 2.83465 points)
                x = x_mm * mm
                # Y coordinate needs to be inverted (PDF origin is bottom-left)
                y = self.page_height - (y_mm * mm)
                
                # Draw text
                c.drawString(x, y, text)
            
            # Save PDF
            c.save()
            
            logger.info(f"PDF created successfully: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to create PDF with ReportLab: {e}")
            raise
    
    def _overlay_text_on_image(self, image: np.ndarray, 
                              extracted_data: List[Dict[str, Any]]) -> np.ndarray:
        """
        Overlay extracted text on image.
        
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
            
            # Put text
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
