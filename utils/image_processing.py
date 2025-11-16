"""Image preprocessing utilities for OCR."""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_skew(image: np.ndarray) -> float:
    """
    Detect skew angle in image using Hough transform.
    
    Args:
        image: Input image (grayscale or BGR)
        
    Returns:
        Skew angle in degrees (positive = counter-clockwise)
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Use HoughLines to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None or len(lines) == 0:
        return 0.0
    
    # Calculate angles of detected lines
    angles = []
    for line in lines[:20]:  # Use first 20 lines
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        # Normalize angle to [-45, 45]
        if angle > 45:
            angle = angle - 90
        elif angle < -45:
            angle = angle + 90
        angles.append(angle)
    
    if not angles:
        return 0.0
    
    # Use median angle (more robust than mean)
    median_angle = np.median(angles)
    
    return float(median_angle)


def correct_skew(image: np.ndarray, angle: float) -> np.ndarray:
    """
    Rotate image to correct skew.
    
    Args:
        image: Input image
        angle: Skew angle in degrees
        
    Returns:
        Rotated image
    """
    if abs(angle) < 0.1:
        return image
    
    # Get image dimensions
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new dimensions to avoid cropping
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix for new dimensions
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    
    # Rotate image
    rotated = cv2.warpAffine(
        image, rotation_matrix, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)  # White background
    )
    
    return rotated


def preprocess_image(image: np.ndarray, enhance_contrast: bool = True) -> np.ndarray:
    """
    Preprocess image for better OCR results.
    
    Args:
        image: Input image (BGR or grayscale)
        enhance_contrast: Whether to apply CLAHE
        
    Returns:
        Preprocessed image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply CLAHE for contrast enhancement
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
    else:
        enhanced = gray
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    
    # Try Otsu threshold (usually best)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return thresh


def deskew(image: np.ndarray) -> np.ndarray:
    """
    Deskew an image by detecting and correcting skew angle.
    
    Args:
        image: Input image (BGR or grayscale)
        
    Returns:
        Deskewed image
    """
    try:
        angle = detect_skew(image)
        if abs(angle) > 0.5:
            logger.info(f"Deskewing image by {angle:.2f} degrees")
            return correct_skew(image, angle)
        return image
    except Exception as e:
        logger.warning(f"Deskew failed: {e}")
        return image


def detect_and_correct_rotation(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct rotation in image (0, 90, 180, 270 degrees).
    
    Args:
        image: Input image
        
    Returns:
        Corrected image
    """
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Use Hough transform to detect orientation
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return image
        
        # Calculate dominant angle
        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            angle = np.degrees(theta)
            angles.append(angle)
        
        if not angles:
            return image
        
        # Determine rotation (simplified - assumes mostly horizontal text)
        median_angle = np.median(angles)
        # Normalize to nearest 90-degree rotation
        rotation = round(median_angle / 90) * 90 - median_angle
        
        if abs(rotation) > 5:
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, rotation, 1.0)
            rotated = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                   flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT,
                                   borderValue=(255, 255, 255))
            logger.info(f"Corrected rotation by {rotation:.2f} degrees")
            return rotated
        
        return image
    except Exception as e:
        logger.warning(f"Rotation detection/correction failed: {e}")
        return image


def align_to_template(image: np.ndarray, template_image: np.ndarray) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Align image to template using feature matching (ORB/AKAZE).
    
    Args:
        image: Image to align
        template_image: Template/reference image
        
    Returns:
        Tuple of (aligned_image, homography_matrix) or (None, None) if alignment fails
    """
    try:
        # Convert to grayscale
        if len(image.shape) == 3:
            img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = image.copy()
        
        if len(template_image.shape) == 3:
            template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template_image.copy()
        
        # Try AKAZE first (better for scale/rotation), fallback to ORB
        detector = None
        try:
            detector = cv2.AKAZE_create()
            kp1, des1 = detector.detectAndCompute(img_gray, None)
            kp2, des2 = detector.detectAndCompute(template_gray, None)
        except Exception:
            logger.debug("AKAZE not available, using ORB")
            detector = cv2.ORB_create(nfeatures=1000)
            kp1, des1 = detector.detectAndCompute(img_gray, None)
            kp2, des2 = detector.detectAndCompute(template_gray, None)
        
        if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
            logger.warning("Not enough features for alignment")
            return None, None
        
        # Match features
        if isinstance(detector, cv2.AKAZE):
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        else:
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        matches = bf.match(des1, des2)
        
        if len(matches) < 10:
            logger.warning(f"Not enough matches ({len(matches)}) for alignment")
            return None, None
        
        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Extract matched keypoints
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Find homography matrix
        homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        if homography is None:
            logger.warning("Failed to compute homography")
            return None, None
        
        # Warp image
        h, w = template_gray.shape[:2]
        if len(image.shape) == 3:
            aligned = cv2.warpPerspective(image, homography, (w, h),
                                         flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_CONSTANT,
                                         borderValue=(255, 255, 255))
        else:
            aligned = cv2.warpPerspective(img_gray, homography, (w, h),
                                         flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_CONSTANT,
                                         borderValue=255)
        
        logger.info("✅ Image aligned to template successfully")
        return aligned, homography
        
    except Exception as e:
        logger.warning(f"Image alignment failed: {e}")
        return None, None


def auto_resize_to_template(image: np.ndarray, template_dims: Dict[str, int]) -> np.ndarray:
    """
    Auto-resize image to match template dimensions with DPI awareness.
    
    Args:
        image: Input image
        template_dims: Dict with 'width' and 'height' keys (in pixels)
        
    Returns:
        Resized image
    """
    try:
        if not template_dims or 'width' not in template_dims or 'height' not in template_dims:
            logger.warning("Invalid template dimensions, skipping resize")
            return image
        
        target_w = template_dims['width']
        target_h = template_dims['height']
        
        img_h, img_w = image.shape[:2]
        
        if img_w == target_w and img_h == target_h:
            logger.debug("Image dimensions already match template")
            return image
        
        logger.info(f"Resizing image from {img_w}x{img_h} to {target_w}x{target_h}")
        resized = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        return resized
        
    except Exception as e:
        logger.warning(f"Auto-resize failed: {e}")
        return image
