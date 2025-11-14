"""Semantic field matching module for mapping OCR text to template fields."""

import re
from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import fuzz, process
from utils.logger import get_logger

logger = get_logger(__name__)


class FieldMatcher:
    """Matches OCR-extracted text to template fields using semantic understanding."""
    
    # Nepali field label keywords and their English equivalents
    FIELD_KEYWORDS = {
        # Name-related fields
        'name': {
            'nepali': ['नाम', 'थर', 'नाम र थर', 'पूरा नाम'],
            'english': ['name', 'full name', 'fullname'],
            'synonyms': ['जग्गा/धनीको नाम', 'सञ्चालकको नाम', 'व्यवसायको नाम', 'धनीको नाम']
        },
        'father_name': {
            'nepali': ['बाबुको नाम', 'पतिको नाम', 'बाबु/पतिको नाम'],
            'english': ['father name', 'husband name', 'father', 'husband'],
            'synonyms': []
        },
        'grandfather_name': {
            'nepali': ['बाजेको नाम', 'ससुराको नाम', 'बाजे/ससुराको नाम'],
            'english': ['grandfather name', 'father-in-law name'],
            'synonyms': []
        },
        'address': {
            'nepali': ['ठेगाना', 'स्थायी ठेगाना', 'पता', 'स्थान'],
            'english': ['address', 'permanent address', 'location'],
            'synonyms': ['व्यवसायको ठेगाना', 'जग्गाधनीको स्थायी ठेगाना']
        },
        'citizenship': {
            'nepali': ['नागरिकता', 'नागरिकता नं', 'नागरिकता नंबर'],
            'english': ['citizenship', 'citizenship number', 'citizenship no'],
            'synonyms': []
        },
        'national_id': {
            'nepali': ['राष्ट्रिय परिचय पत्र', 'राष्ट्रिय परिचय पत्र नं', 'परिचय पत्र नं'],
            'english': ['national id', 'national identity', 'id number', 'id card'],
            'synonyms': ['राष्ट्रिय परिचय पत्र नं']
        },
        'date_of_birth': {
            'nepali': ['जन्म मिति', 'जन्म तारिख', 'जन्म मिति'],
            'english': ['date of birth', 'birth date', 'dob', 'birthday'],
            'synonyms': []
        },
        'mobile': {
            'nepali': ['मोबाइल', 'मोबाइल नं', 'मोबाइल नंबर', 'फोन', 'फोन नं'],
            'english': ['mobile', 'mobile number', 'phone', 'phone number', 'contact'],
            'synonyms': []
        },
        'email': {
            'nepali': ['ई-मेल', 'इमेल', 'ईमेल'],
            'english': ['email', 'e-mail', 'mail'],
            'synonyms': []
        },
        'registration_date': {
            'nepali': ['दर्ता मिति', 'दर्ता तारिख'],
            'english': ['registration date', 'reg date'],
            'synonyms': []
        },
        'business_operation_date': {
            'nepali': ['व्यवसाय सञ्चालन मिति', 'सञ्चालन मिति'],
            'english': ['operation date', 'business start date'],
            'synonyms': []
        },
        'pan_number': {
            'nepali': ['पान नं', 'पान नंबर', 'पान नं'],
            'english': ['pan number', 'pan no', 'pan'],
            'synonyms': ['व्यवसायको पान नं']
        },
        'economic_code': {
            'nepali': ['आन्तरिक संकेत नं', 'आन्तरिक संकेत'],
            'english': ['economic code', 'economic indicator'],
            'synonyms': []
        },
        'ward_office': {
            'nepali': ['वडा कार्यालय', 'वडा'],
            'english': ['ward office', 'ward'],
            'synonyms': []
        },
        'business_type': {
            'nepali': ['व्यवसायको किसिम', 'किसिम'],
            'english': ['business type', 'type'],
            'synonyms': []
        },
        'street_name': {
            'nepali': ['पथ', 'टोल', 'पथ/टोलको नाम'],
            'english': ['street', 'lane', 'street name'],
            'synonyms': []
        },
        'capital': {
            'nepali': ['पूँजी', 'कुल पूँजी'],
            'english': ['capital', 'total capital'],
            'synonyms': []
        },
        'local_registration': {
            'nepali': ['स्थानीय दर्ता नं', 'स्थानीय दर्ता'],
            'english': ['local registration', 'local reg'],
            'synonyms': []
        },
    }
    
    def __init__(self, confidence_threshold: float = 0.5, debug: bool = False):
        """
        Initialize field matcher.
        
        Args:
            confidence_threshold: Minimum fuzzy match score (0-1) to accept a match (lowered to 0.5 for better matching)
            debug: Enable debug logging for mapping decisions
        """
        self.confidence_threshold = confidence_threshold
        self.debug = debug
        logger.info(f"Initialized FieldMatcher (threshold={confidence_threshold}, debug={debug})")
    
    def parse_ocr_line(self, ocr_line: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """
        Parse an OCR text line to extract field label and value.
        
        Handles formats like:
        - "नाम : हसन गाहा"
        - "ठेगाना : काठमाण्डौ"
        - "Name: John Doe"
        - "नाम – हसन गाहा" (using en-dash or em-dash)
        
        Args:
            ocr_line: Dict with 'text' and optionally 'confidence'
            
        Returns:
            Tuple of (field_label, field_value) or None if parsing fails
        """
        text = ocr_line.get('text', '').strip()
        if not text:
            return None
        
        # Try different separators: colon, en-dash, em-dash, hyphen, pipe, double space, tab
        separators = [':', '–', '—', '-', '|', '  ', '\t', ' :', ': ', ' -', '- ']
        
        for sep in separators:
            if sep in text:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Clean up common OCR artifacts but preserve Nepali characters
                    label = re.sub(r'[^\w\s\u0900-\u097F]', '', label)  # Keep Nepali + English alphanumeric
                    value = re.sub(r'^\s*[:\-–—|\s]+\s*', '', value)  # Remove leading separators from value
                    value = value.strip()
                    
                    # Only return if we have meaningful label and value
                    if label and value and len(label) > 0 and len(value) > 0:
                        return (label, value)
        
        # If no separator found, try to detect if it's a label-value pair
        # by checking if it starts with known keywords
        for category, keywords in self.FIELD_KEYWORDS.items():
            all_keywords = keywords['nepali'] + keywords['english'] + keywords.get('synonyms', [])
            for keyword in all_keywords:
                if text.lower().startswith(keyword.lower()):
                    # Try to extract value after keyword
                    remaining = text[len(keyword):].strip()
                    if remaining:
                        # Remove common separators from start
                        remaining = re.sub(r'^[:\-–—|\s]+', '', remaining)
                        if remaining:
                            return (keyword, remaining)
        
        return None
    
    def extract_field_label(self, template_field: Dict[str, Any]) -> str:
        """
        Extract the best label text from a template field.
        
        Args:
            template_field: Template field dict with 'name', 'label', etc.
            
        Returns:
            Best available label string
        """
        # Prefer Nepali name, fallback to English label
        name = template_field.get('name', '')
        label = template_field.get('label', '')
        
        if name:
            return name
        return label
    
    def match_field_keywords(self, field_label: str, category: str) -> float:
        """
        Check if a field label matches keywords in a category.
        
        Args:
            field_label: Label to check
            category: Category name from FIELD_KEYWORDS
            
        Returns:
            Match score (0-1)
        """
        if category not in self.FIELD_KEYWORDS:
            return 0.0
        
        keywords = self.FIELD_KEYWORDS[category]
        all_keywords = keywords['nepali'] + keywords['english'] + keywords.get('synonyms', [])
        
        field_lower = field_label.lower()
        
        # Direct match
        for keyword in all_keywords:
            if keyword.lower() in field_lower or field_lower in keyword.lower():
                return 1.0
        
        # Fuzzy match
        best_match = process.extractOne(field_label, all_keywords, scorer=fuzz.partial_ratio)
        if best_match:
            score = best_match[1] / 100.0
            return score
        
        return 0.0
    
    def find_best_category(self, field_label: str) -> Optional[Tuple[str, float]]:
        """
        Find the best matching category for a field label.
        
        Args:
            field_label: Field label to categorize
            
        Returns:
            Tuple of (category_name, match_score) or None
        """
        best_category = None
        best_score = 0.0
        
        for category in self.FIELD_KEYWORDS.keys():
            score = self.match_field_keywords(field_label, category)
            if score > best_score:
                best_score = score
                best_category = category
        
        if best_score >= self.confidence_threshold:
            return (best_category, best_score)
        
        return None
    
    def fuzzy_match_labels(self, ocr_label: str, template_label: str) -> float:
        """
        Perform fuzzy matching between OCR label and template label.
        
        Args:
            ocr_label: Label extracted from OCR
            template_label: Label from template field
            
        Returns:
            Similarity score (0-1)
        """
        # Direct match
        if ocr_label.lower() == template_label.lower():
            return 1.0
        
        # Partial ratio (handles substring matches)
        partial_score = fuzz.partial_ratio(ocr_label.lower(), template_label.lower()) / 100.0
        
        # Token sort ratio (handles word order differences)
        token_score = fuzz.token_sort_ratio(ocr_label.lower(), template_label.lower()) / 100.0
        
        # Use the maximum of both
        return max(partial_score, token_score)
    
    def match_ocr_to_template(
        self,
        ocr_lines: List[Dict[str, Any]],
        template_fields: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Match OCR-extracted text lines to template fields semantically.
        
        Args:
            ocr_lines: List of OCR text lines, each with 'text' and optionally 'confidence'
            template_fields: List of template field definitions
            
        Returns:
            Dict mapping template_field_id to matched data {name, text, confidence, bbox}
        """
        logger.info(f"Starting semantic field matching: {len(ocr_lines)} OCR lines → {len(template_fields)} template fields")
        
        # Parse OCR lines into label-value pairs
        parsed_ocr = []
        for line in ocr_lines:
            parsed = self.parse_ocr_line(line)
            if parsed:
                label, value = parsed
                parsed_ocr.append({
                    'label': label,
                    'value': value,
                    'confidence': line.get('confidence', 0.8),
                    'bbox': line.get('bbox', {})
                })
        
        logger.info(f"Parsed {len(parsed_ocr)} label-value pairs from OCR")
        
        # Match each template field to best OCR value
        matched_data = {}
        
        for template_field in template_fields:
            field_id = template_field.get('id', template_field.get('name', 'unknown'))
            template_label = self.extract_field_label(template_field)
            
            best_match = None
            best_score = 0.0
            best_ocr_item = None
            
            # Try category-based matching first
            category_result = self.find_best_category(template_label)
            if category_result:
                category, category_score = category_result
                
                # Find OCR items that match this category
                for ocr_item in parsed_ocr:
                    ocr_category_result = self.find_best_category(ocr_item['label'])
                    if ocr_category_result and ocr_category_result[0] == category:
                        # Category match - use fuzzy score for ranking
                        fuzzy_score = self.fuzzy_match_labels(ocr_item['label'], template_label)
                        combined_score = (category_score * 0.6) + (fuzzy_score * 0.4)
                        
                        if combined_score > best_score:
                            best_score = combined_score
                            best_match = ocr_item['value']
                            best_ocr_item = ocr_item
            
            # If no category match, try direct fuzzy matching
            if best_score < self.confidence_threshold:
                for ocr_item in parsed_ocr:
                    fuzzy_score = self.fuzzy_match_labels(ocr_item['label'], template_label)
                    
                    if fuzzy_score > best_score:
                        best_score = fuzzy_score
                        best_match = ocr_item['value']
                        best_ocr_item = ocr_item
            
            # Store match if above threshold
            if best_score >= self.confidence_threshold and best_match:
                matched_data[field_id] = {
                    'name': template_label,
                    'text': best_match,
                    'confidence': min(best_score, best_ocr_item['confidence']),
                    'bbox': template_field.get('bbox', {}),
                    'match_score': best_score,
                    'matched_from': best_ocr_item['label']
                }
                
                if self.debug:
                    logger.debug(
                        f"✅ Matched '{best_ocr_item['label']} : {best_match}' → "
                        f"'{template_label}' (score: {best_score:.2f})"
                    )
            else:
                # Log unmatched fields
                if self.debug:
                    logger.debug(
                        f"⚠️ No match found for template field '{template_label}' "
                        f"(best score: {best_score:.2f}, threshold: {self.confidence_threshold})"
                    )
                
                # Still create entry with empty text for validation
                matched_data[field_id] = {
                    'name': template_label,
                    'text': '',
                    'confidence': 0.0,
                    'bbox': template_field.get('bbox', {}),
                    'match_score': best_score
                }
        
        matched_count = sum(1 for v in matched_data.values() if v.get('text'))
        logger.info(
            f"✅ Field matching complete: {matched_count}/{len(template_fields)} fields matched "
            f"(threshold: {self.confidence_threshold})"
        )
        
        return matched_data
    
    def match_from_full_ocr(
        self,
        ocr_result: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Match OCR result (from extract_from_image) to template fields.
        
        Args:
            ocr_result: Full OCR result dict with 'lines' key
            template: Template dict with field definitions
            
        Returns:
            Dict mapping field_id to matched data
        """
        # Extract OCR lines
        ocr_lines = ocr_result.get('lines', [])
        if not ocr_lines:
            logger.warning("No OCR lines found in result")
            return {}
        
        # Extract template fields
        if 'fields' in template:
            template_fields = template['fields']
        elif 'forms' in template and template['forms']:
            template_fields = template['forms'][0]['fields']
        else:
            logger.error("Invalid template format: missing 'fields' or 'forms'")
            return {}
        
        return self.match_ocr_to_template(ocr_lines, template_fields)

