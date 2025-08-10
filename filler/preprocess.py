"""
Image and PDF Preprocessing Module

Handles conversion of PDFs to images and image normalization
for consistent OCR processing.
"""

import os
from typing import List, Union
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class PreprocessorService:
    """Service for preprocessing input files for OCR processing."""
    
    def __init__(self, dpi: int = 300, target_width: int = 2480):
        """
        Initialize preprocessor with configuration.
        
        Args:
            dpi: DPI for PDF to image conversion
            target_width: Target width for image normalization
        """
        self.dpi = dpi
        self.target_width = target_width
    
    def process_input(self, input_path: str) -> List[Image.Image]:
        """
        Process input file (PDF or image) and return list of normalized images.
        
        Args:
            input_path: Path to input file
            
        Returns:
            List[Image.Image]: List of processed images (one per page)
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If input file doesn't exist
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_ext = Path(input_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self._process_pdf(input_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return self._process_image(input_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    def _process_pdf(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF to images and normalize.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List[Image.Image]: List of normalized images
            
        Raises:
            RuntimeError: If PDF processing is not supported
        """
        if not PDF_SUPPORT:
            raise RuntimeError(
                "PDF processing not supported. Install pdf2image: pip install pdf2image"
            )
        
        print(f"Converting PDF to images (DPI: {self.dpi})...")
        images = convert_from_path(pdf_path, dpi=self.dpi)
        
        normalized_images = []
        for i, image in enumerate(images):
            print(f"Processing page {i + 1}/{len(images)}...")
            normalized_image = self._normalize_image(image)
            normalized_images.append(normalized_image)
        
        return normalized_images
    
    def _process_image(self, image_path: str) -> List[Image.Image]:
        """
        Load and normalize a single image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List[Image.Image]: List containing single normalized image
        """
        print(f"Loading and processing image...")
        image = Image.open(image_path)
        normalized_image = self._normalize_image(image)
        return [normalized_image]
    
    def _normalize_image(self, image: Image.Image) -> Image.Image:
        """
        Normalize image size and quality for consistent OCR processing.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Image.Image: Normalized image
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize to target width while maintaining aspect ratio
        width, height = image.size
        if width != self.target_width:
            target_height = int((height * self.target_width) / width)
            image = image.resize(
                (self.target_width, target_height), 
                Image.Resampling.LANCZOS
            )
        
        # Apply image enhancement for better OCR
        image_array = np.array(image)
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # Apply adaptive threshold to improve text clarity
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply slight gaussian blur to reduce noise
        denoised = cv2.GaussianBlur(binary, (1, 1), 0)
        
        # Convert back to PIL Image
        processed_image = Image.fromarray(denoised).convert('RGB')
        
        return processed_image
    
    def save_debug_image(self, image: Image.Image, output_path: str) -> None:
        """
        Save processed image for debugging purposes.
        
        Args:
            image: Processed PIL Image
            output_path: Path to save debug image
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, quality=95)
        print(f"Debug image saved: {output_path}")