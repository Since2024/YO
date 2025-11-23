"""Simple file-based cache for extraction results."""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from app import data_dir
from app.utils import get_logger

logger = get_logger(__name__)

CACHE_DIR = data_dir() / ".cache"
CACHE_TTL_HOURS = 24


def _get_cache_key(image_hashes: List[str], template_hash: str) -> str:
    """Generate cache key from image and template hashes."""
    combined = "".join(sorted(image_hashes)) + template_hash
    return hashlib.sha256(combined.encode()).hexdigest()


def get_cached_extraction(
    image_hashes: List[str],
    template_hash: str
) -> Optional[Dict]:
    """Retrieve cached extraction if available and fresh."""
    cache_key = _get_cache_key(image_hashes, template_hash)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Check TTL
        cached_at = datetime.fromisoformat(data['cached_at'])
        age = datetime.now() - cached_at
        
        if age > timedelta(hours=CACHE_TTL_HOURS):
            logger.debug("Cache expired for key %s (age: %s)", cache_key[:16], age)
            cache_file.unlink()
            return None
        
        logger.info("Cache hit for key %s", cache_key[:16])
        return data['extraction']
        
    except Exception as e:
        logger.warning("Error reading cache: %s", e)
        cache_file.unlink(missing_ok=True)
        return None


def set_cached_extraction(
    image_hashes: List[str],
    template_hash: str,
    extraction: Dict
) -> None:
    """Store extraction result in cache."""
    cache_key = _get_cache_key(image_hashes, template_hash)
    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        data = {
            'cached_at': datetime.now().isoformat(),
            'extraction': extraction,
            'image_hashes': image_hashes,
            'template_hash': template_hash,
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Cached extraction for key %s", cache_key[:16])
        
    except Exception as e:
        logger.warning("Error writing cache: %s", e)


def clear_cache() -> int:
    """Clear all cached extractions. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0
    
    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception as e:
            logger.warning("Error deleting cache file %s: %s", cache_file, e)
    
    logger.info("Cleared %d cache files", count)
    return count

