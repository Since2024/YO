"""Field format validators for extracted data."""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class FieldValidator:
    """Validates field formats and normalizes data."""
    
    # Nepali date patterns (BS dates)
    NEPALI_DATE_PATTERNS = [
        r'(\d{4})[-\s/](\d{1,2})[-\s/](\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})[-\s/](\d{1,2})[-\s/](\d{4})',  # DD-MM-YYYY
    ]
    
    # Phone number patterns (Nepal)
    PHONE_PATTERNS = [
        r'^(\+977)?[-\s]?9[678]\d{8}$',  # Mobile: 98XXXXXXXX or 97XXXXXXXX
        r'^0?[1-9]\d{6,7}$',  # Landline
    ]
    
    # Citizenship number pattern (Nepal)
    CITIZENSHIP_PATTERN = r'^\d{1,2}-\d{2}-\d{5,6}$'  # Format: XX-XX-XXXXX
    
    # PAN number pattern (Nepal)
    PAN_PATTERN = r'^[A-Z]{5}\d{4}[A-Z]$'  # Format: XXXXX1234X
    
    @staticmethod
    def validate_date(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and normalize date format.
        
        Args:
            text: Date string to validate
            
        Returns:
            Tuple of (is_valid, normalized_date)
        """
        if not text or not text.strip():
            return (False, None)
        
        text = text.strip()
        
        # Try to parse as Nepali date
        for pattern in FieldValidator.NEPALI_DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # Try to normalize to YYYY-MM-DD format
                    try:
                        # Assume first group is year if 4 digits
                        if len(groups[0]) == 4:
                            year, month, day = groups
                        else:
                            day, month, year = groups
                        
                        normalized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        return (True, normalized)
                    except:
                        pass
        
        # If no pattern matches, return original but mark as potentially invalid
        return (False, text)
    
    @staticmethod
    def validate_phone(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate and normalize phone number.
        
        Args:
            text: Phone number string
            
        Returns:
            Tuple of (is_valid, normalized_phone)
        """
        if not text or not text.strip():
            return (False, None)
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', text.strip())
        
        # Remove country code if present
        if cleaned.startswith('+977'):
            cleaned = cleaned[4:]
        elif cleaned.startswith('977'):
            cleaned = cleaned[3:]
        
        # Validate format
        for pattern in FieldValidator.PHONE_PATTERNS:
            if re.match(pattern, cleaned):
                # Normalize to 10 digits
                if len(cleaned) == 10:
                    return (True, cleaned)
                elif len(cleaned) == 9:
                    return (True, '0' + cleaned)
        
        return (False, cleaned)
    
    @staticmethod
    def validate_citizenship(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate citizenship number format.
        
        Args:
            text: Citizenship number string
            
        Returns:
            Tuple of (is_valid, normalized_citizenship)
        """
        if not text or not text.strip():
            return (False, None)
        
        cleaned = text.strip().upper()
        
        # Check format
        if re.match(FieldValidator.CITIZENSHIP_PATTERN, cleaned):
            return (True, cleaned)
        
        # Try to normalize (remove spaces, add dashes)
        cleaned = re.sub(r'[^\d]', '', cleaned)
        if len(cleaned) >= 8:
            # Format: XX-XX-XXXXX
            formatted = f"{cleaned[:2]}-{cleaned[2:4]}-{cleaned[4:]}"
            if re.match(FieldValidator.CITIZENSHIP_PATTERN, formatted):
                return (True, formatted)
        
        return (False, cleaned)
    
    @staticmethod
    def validate_pan(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate PAN number format.
        
        Args:
            text: PAN number string
            
        Returns:
            Tuple of (is_valid, normalized_pan)
        """
        if not text or not text.strip():
            return (False, None)
        
        cleaned = text.strip().upper()
        
        # Remove spaces and dashes
        cleaned = re.sub(r'[-\s]', '', cleaned)
        
        if re.match(FieldValidator.PAN_PATTERN, cleaned):
            return (True, cleaned)
        
        return (False, cleaned)
    
    @staticmethod
    def validate_email(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.
        
        Args:
            text: Email string
            
        Returns:
            Tuple of (is_valid, normalized_email)
        """
        if not text or not text.strip():
            return (False, None)
        
        email = text.strip().lower()
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return (True, email)
        
        return (False, email)
    
    @staticmethod
    def validate_numeric(text: str, min_length: Optional[int] = None, 
                        max_length: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate numeric field.
        
        Args:
            text: Numeric string
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            Tuple of (is_valid, normalized_number)
        """
        if not text or not text.strip():
            return (False, None)
        
        # Remove non-digit characters
        cleaned = re.sub(r'[^\d]', '', text.strip())
        
        if not cleaned:
            return (False, None)
        
        # Check length constraints
        if min_length and len(cleaned) < min_length:
            return (False, cleaned)
        if max_length and len(cleaned) > max_length:
            return (False, cleaned)
        
        return (True, cleaned)
    
    @staticmethod
    def validate_field(field_data: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """
        Validate and normalize a field based on its type.
        
        Args:
            field_data: Field data dict with 'text' key
            field_type: Field type (date, phone, citizenship, pan, email, number)
            
        Returns:
            Updated field_data with validation results
        """
        text = field_data.get('text', '').strip()
        
        if not text:
            field_data['valid'] = False
            field_data['normalized'] = None
            return field_data
        
        is_valid = False
        normalized = text
        
        if field_type == 'date':
            is_valid, normalized = FieldValidator.validate_date(text)
        elif field_type == 'phone' or field_type == 'mobile':
            is_valid, normalized = FieldValidator.validate_phone(text)
        elif field_type == 'citizenship':
            is_valid, normalized = FieldValidator.validate_citizenship(text)
        elif field_type == 'pan':
            is_valid, normalized = FieldValidator.validate_pan(text)
        elif field_type == 'email':
            is_valid, normalized = FieldValidator.validate_email(text)
        elif field_type == 'number' or field_type == 'numeric':
            min_len = field_data.get('validate', {}).get('min_len')
            max_len = field_data.get('validate', {}).get('max_len')
            is_valid, normalized = FieldValidator.validate_numeric(text, min_len, max_len)
        else:
            # Text field - no validation, just normalize whitespace
            normalized = ' '.join(text.split())
            is_valid = True
        
        field_data['valid'] = is_valid
        field_data['normalized'] = normalized
        
        if normalized and normalized != text:
            field_data['text'] = normalized  # Update with normalized value
            logger.debug(f"Normalized field: '{text}' → '{normalized}'")
        
        return field_data

