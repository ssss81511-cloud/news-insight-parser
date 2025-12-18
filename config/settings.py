"""
Project configuration settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# API Credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
PRODUCT_HUNT_API_KEY = os.getenv("PRODUCT_HUNT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/insights.db")

# Scraping settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
RATE_LIMIT_DELAY = int(os.getenv("RATE_LIMIT_DELAY", 2))

# Data sources configuration
DATA_SOURCES = {
    "indie_hackers": {
        "enabled": True,
        "base_url": "https://www.indiehackers.com",
        "sections": ["discussions", "comments"]
    },
    "hacker_news": {
        "enabled": True,
        "base_url": "https://news.ycombinator.com",
        "sections": ["new", "ask"]
    },
    "product_hunt": {
        "enabled": True,
        "base_url": "https://www.producthunt.com",
        "sections": ["launches", "comments"]
    },
    "reddit": {
        "enabled": True,
        "subreddits": ["SaaS", "startups", "Entrepreneur"]
    },
    "vc_blogs": {
        "enabled": True,
        "blogs": [
            "https://a16z.com/blog/",
            "https://www.ycombinator.com/blog/"
        ]
    }
}

# Analysis settings
SIGNAL_THRESHOLDS = {
    "min_pain_mentions": 3,  # Minimum mentions to consider a pain point
    "min_pattern_occurrences": 2,  # Minimum occurrences for solution pattern
    "lookback_days": 30  # Days to look back for pattern detection
}
