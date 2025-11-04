"""
PDF Generation Module

Handles creation of filled PDF forms using ReportLab with pixel-perfect
positioning based on template coordinates.
"""

import os
from typing import Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black


class PDFGenerator:
    """Service for generating filled PDF forms."""
    
    def __init__(self, page_size=A4, font_name: str = 'Helvetica', font_size: int = 10):
        """
        Initialize PDF generator.
        
        Args:
            page_size: PDF page size (default: A4)
            font_name: Default font name
            font_size: Default font size
        """
        self.page_size = page_size
        self.default_font_name = font_name
        self.default_font_size = font_size
        
        # PDF dimensions (ReportLab uses bottom-left origin)
        self.page_width, self.page_height = page_size
    
    def create_filled_pdf(self, template_data: Dict[str, Any], 
                         extracted_data: Dict[str, Dict[str, Any]], 
                         output_path: str) -> None:
        """
        Create a filled PDF form based on template and extracted data.
        
        Args:
            template_data: Template configuration
            extracted_data: OCR extracted data
            output_path: Path to save the generated PDF
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=self.page_size)
        
        # Group fields by page
        pages_data = self._group_fields_by_page(template_data, extracted_data)
        
        # Process each page
        for page_num in sorted(pages_data.keys()):
            if page_num > 1:
                c.showPage()  # Start new page
            
            self._fill_page(c, pages_data[page_num])
        
        # Save the PDF
        c.save()
        print(f"PDF generated successfully: {output_path}")
    
    def _group_fields_by_page(self, template_data: Dict[str, Any], 
                             extracted_data: Dict[str, Dict[str, Any]]) -> Dict[int, list]:
        """
        Group fields by page number for multi-page processing.
        
        Args:
            template_data: Template configuration
            extracted_data: OCR extracted data
            
        Returns:
            Dict[int, list]: Fields grouped by page number
        """
        pages_data = {}
        
        for field in template_data['fields']:
            page_num = field.get('page', 1)
            field_name = field['name']
            
            # Get extracted text for this field
            extracted_text = ''
            if field_name in extracted_data:
                extracted_text = extracted_data[field_name].get('text', '')
            
            # Combine field info with extracted text
            field_data = {
                'field': field,
                'extracted_text': extracted_text,
                'confidence': extracted_data.get(field_name, {}).get('confidence', 0.0)
            }
            
            if page_num not in pages_data:
                pages_data[page_num] = []
            pages_data[page_num].append(field_data)
        
        return pages_data
    
    def _fill_page(self, canvas: canvas.Canvas, page_fields: list) -> None:
        """
        Fill a single page with field data.
        
        Args:
            canvas: ReportLab canvas object
            page_fields: List of field data for this page
        """
        # Set default font
        canvas.setFont(self.default_font_name, self.default_font_size)
        canvas.setFillColor(black)
        
        for field_data in page_fields:
            field = field_data['field']
            text = field_data['extracted_text']
            confidence = field_data['confidence']
            
            if text:  # Only draw if there's text to display
                self._draw_field_text(canvas, field, text, confidence)
    
    def _draw_field_text(self, canvas: canvas.Canvas, field: Dict[str, Any], 
                        text: str, confidence: float) -> None:
        """
        Draw text at the specified field position.
        
        Args:
            canvas: ReportLab canvas object
            field: Field configuration
            text: Text to draw
            confidence: OCR confidence score
        """
        # Get field coordinates
        x = field['x']
        y = field['y']
        width = field['width']
        height = field['height']
        
        # Convert coordinates from top-left origin to bottom-left origin (ReportLab)
        # ReportLab uses bottom-left as (0,0), so we need to flip Y coordinate
        pdf_x = x
        pdf_y = self.page_height - y - height  # Flip Y coordinate
        
        # Determine font size based on field height
        font_size = min(self.default_font_size, int(height * 0.6))
        if font_size < 6:
            font_size = 6
        
        # Set font size
        canvas.setFontSize(font_size)
        
        # Handle text that might be too long for the field
        text = self._fit_text_to_width(canvas, text, width, font_size)
        
        # Draw the text
        try:
            canvas.drawString(pdf_x, pdf_y + (height - font_size) / 2, text)
        except Exception as e:
            print(f"Warning: Could not draw text for field {field['name']}: {e}")
            # Fallback to simple ASCII text
            ascii_text = text.encode('ascii', 'ignore').decode('ascii')
            if ascii_text:
                canvas.drawString(pdf_x, pdf_y + (height - font_size) / 2, ascii_text)
        
        # Add confidence indicator if in debug mode (optional)
        # This could be controlled by a parameter in the future
        # if confidence < 70.0:
        #     canvas.setFillColor(red)
        #     canvas.drawString(pdf_x + width + 5, pdf_y, f"({confidence:.0f}%)")
        #     canvas.setFillColor(black)
    
    def _fit_text_to_width(self, canvas: canvas.Canvas, text: str, 
                          max_width: float, font_size: int) -> str:
        """
        Truncate text to fit within the specified width.
        
        Args:
            canvas: ReportLab canvas object
            text: Original text
            max_width: Maximum width in points
            font_size: Font size
            
        Returns:
            str: Text that fits within the width
        """
        if not text:
            return text
        
        # Get text width
        text_width = canvas.stringWidth(text, self.default_font_name, font_size)
        
        if text_width <= max_width:
            return text
        
        # Truncate text with ellipsis
        ellipsis = "..."
        ellipsis_width = canvas.stringWidth(ellipsis, self.default_font_name, font_size)
        available_width = max_width - ellipsis_width
        
        if available_width <= 0:
            return ""
        
        # Binary search for the longest text that fits
        left, right = 0, len(text)
        result = ""
        
        while left <= right:
            mid = (left + right) // 2
            test_text = text[:mid]
            test_width = canvas.stringWidth(test_text, self.default_font_name, font_size)
            
            if test_width <= available_width:
                result = test_text
                left = mid + 1
            else:
                right = mid - 1
        
        return result + ellipsis if result != text else text
    
    def create_blank_form(self, template_data: Dict[str, Any], output_path: str) -> None:
        """
        Create a blank form with field outlines for template design.
        
        Args:
            template_data: Template configuration
            output_path: Path to save the blank form
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=self.page_size)
        
        # Group fields by page
        pages = {}
        for field in template_data['fields']:
            page_num = field.get('page', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(field)
        
        # Draw each page
        for page_num in sorted(pages.keys()):
            if page_num > 1:
                c.showPage()
            
            c.setFont(self.default_font_name, 8)
            
            for field in pages[page_num]:
                x = field['x']
                y = field['y']
                width = field['width']
                height = field['height']
                
                # Convert to PDF coordinates
                pdf_x = x
                pdf_y = self.page_height - y - height
                
                # Draw field rectangle
                c.rect(pdf_x, pdf_y, width, height, fill=0, stroke=1)
                
                # Draw field name
                c.drawString(pdf_x + 2, pdf_y + height + 2, field['name'])
        
        c.save()
        print(f"Blank form created: {output_path}")