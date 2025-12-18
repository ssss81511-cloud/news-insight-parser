"""
Common utility functions
"""
import re
from datetime import datetime, timezone
from typing import List


def clean_html(text: str) -> str:
    """Remove HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean = clean.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    clean = clean.replace('&#x27;', "'").replace('&quot;', '"')
    return clean.strip()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract potential keywords from text"""
    if not text:
        return []

    # Remove HTML and special characters
    clean = clean_html(text).lower()
    # Split into words
    words = re.findall(r'\b[a-z]{' + str(min_length) + r',}\b', clean)
    # Remove common words
    stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
    keywords = [w for w in words if w not in stopwords]

    return keywords


def time_ago(dt: datetime) -> str:
    """Convert datetime to 'time ago' format"""
    if not dt:
        return "unknown"

    # Make sure both datetimes are timezone-aware
    now = datetime.now(timezone.utc)

    # If dt is naive (no timezone), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max length"""
    if not text:
        return ""
    text = clean_html(text)
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + '...'
