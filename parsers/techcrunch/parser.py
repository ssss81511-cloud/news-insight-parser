"""
TechCrunch Parser - RSS-based parser for tech news

Parses TechCrunch RSS feeds for:
- Startup launches and announcements
- Funding rounds and acquisitions
- Tech market trends
- App releases
"""
import re
import time
from typing import List, Optional
from datetime import datetime, timezone
import requests
import feedparser
from loguru import logger

from parsers.base_parser import BaseParser


class TechCrunchParser(BaseParser):
    """
    Parser for TechCrunch RSS feeds

    Features:
    - No authentication required
    - RSS-based parsing
    - Multiple category feeds
    - Focus detection for funding/launches
    """

    def __init__(self):
        super().__init__(source_name='techcrunch')
        self.BASE_URL = 'https://techcrunch.com'
        self.headers = {
            'User-Agent': 'NewsInsightParser/2.0 (Educational Project)',
            'Accept': 'application/rss+xml, application/xml, text/xml'
        }

    # Category RSS feeds
    CATEGORIES = {
        'main': {
            'feed_url': 'https://techcrunch.com/feed/',
            'description': 'TechCrunch Main - все новости'
        },
        'startups': {
            'feed_url': 'https://techcrunch.com/category/startups/feed/',
            'description': 'Startups - запуски и новости стартапов'
        },
        'funding': {
            'feed_url': 'https://techcrunch.com/category/venture/feed/',
            'description': 'Venture - раунды финансирования'
        },
        'apps': {
            'feed_url': 'https://techcrunch.com/category/apps/feed/',
            'description': 'Apps - новые приложения и продукты'
        }
    }

    # Focus themes for importance scoring
    FOCUS_THEMES = [
        r"raise[sd]?\s+\$\d+",  # "raised $10M"
        r"series\s+[abc]",  # "Series A"
        r"funding\s+round",
        r"acquisition",
        r"acquired?\s+by",
        r"launch(?:es|ed|ing)?",
        r"announces?\s+(?:new|launch)",
        r"valuation",
        r"unicorn",
        r"ipo",
        r"saas",
        r"b2b",
        r"ai[- ]powered",
        r"startup\s+(?:raises|launches|announces)"
    ]

    def get_available_sections(self) -> List[str]:
        """Get list of available TechCrunch categories"""
        return list(self.CATEGORIES.keys())

    def fetch_posts(self, section: str, limit: int = 20) -> List[dict]:
        """
        Fetch posts from TechCrunch RSS feed

        Args:
            section: Category name (main/startups/funding/apps)
            limit: Max items to return (RSS typically returns ~20)

        Returns:
            List of raw post dicts
        """
        if section not in self.CATEGORIES:
            raise ValueError(f"Unknown section: {section}. Available: {list(self.CATEGORIES.keys())}")

        feed_url = self.CATEGORIES[section]['feed_url']

        try:
            logger.info(f"Fetching TechCrunch/{section} from {feed_url}")

            response = requests.get(
                feed_url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"No entries in TechCrunch/{section} feed")
                return []

            # Convert feedparser entries to our format
            posts = []
            for entry in feed.entries[:limit]:
                posts.append({
                    'title': entry.get('title', 'No title'),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'author': entry.get('author', 'TechCrunch'),
                    'tags': [tag.get('term', '') for tag in entry.get('tags', [])],
                    'id': entry.get('id', entry.get('link', '')),
                    'category_id': section  # Add section info to each post
                })

            logger.info(f"✓ TechCrunch/{section}: fetched {len(posts)} articles")
            return posts

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for TechCrunch/{section}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing TechCrunch/{section}: {e}")
            raise

    def _detect_focus_themes(self, text: str) -> bool:
        """
        Detect if text contains focus themes

        Args:
            text: Text to analyze

        Returns:
            True if contains focus themes
        """
        text_lower = text.lower()
        for pattern in self.FOCUS_THEMES:
            if re.search(pattern, text_lower):
                return True
        return False

    def normalize_post(self, raw_post: dict) -> Optional[dict]:
        """
        Convert TechCrunch RSS entry to UniversalPost format

        Args:
            raw_post: Raw RSS entry dict (includes 'category_id')

        Returns:
            Normalized post dictionary or None
        """
        try:
            # Extract data
            title = raw_post.get('title', '').strip()
            url = raw_post.get('link', '').strip()

            if not title or not url:
                logger.warning("Skipping post: missing title or URL")
                return None

            # Get category from raw_post
            section = raw_post.get('category_id', 'main')

            # Body/content
            summary = raw_post.get('summary', '').strip()
            # Clean HTML tags from summary
            body = re.sub(r'<[^>]+>', '', summary)

            # Author
            author = raw_post.get('author', 'TechCrunch')

            # Published date
            published_str = raw_post.get('published', '')
            created_at = None
            if published_str:
                try:
                    # feedparser provides time_struct
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(published_str)
                    # Ensure timezone-aware datetime
                    created_at = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except:
                    created_at = datetime.now(timezone.utc)
            else:
                created_at = datetime.now(timezone.utc)

            # Tags
            tags = raw_post.get('tags', [])

            # Detect focus themes
            combined_text = f"{title} {body}"
            has_focus = self._detect_focus_themes(combined_text)

            # Determine post type
            post_type = 'news'
            if section == 'funding':
                post_type = 'funding'
            elif section == 'startups':
                post_type = 'launch'

            # Create normalized dictionary
            normalized = {
                'source': 'techcrunch',
                'source_id': raw_post.get('id', url),
                'source_url': url,
                'title': title,
                'content': body[:1000] if body else None,  # Limit summary length
                'author': author,
                'score': 0,  # RSS doesn't provide scores
                'comments_count': 0,  # RSS doesn't provide comment counts
                'post_type': post_type,
                'category': section,
                'created_at': created_at,
                'metadata': {
                    'tags': tags,
                    'has_focus_themes': has_focus,
                    'category': section,
                    'feed_url': self.CATEGORIES[section]['feed_url']
                }
            }

            # Generate content hash
            normalized['content_hash'] = self.generate_content_hash(
                normalized['title'],
                normalized['content'] or ''
            )

            # Calculate importance score
            base_score = 50  # Base score for TechCrunch articles

            # Bonus for focus themes
            if has_focus:
                base_score = min(100, base_score + 20)  # +20 for funding/launches
                logger.info(f"Focus theme detected in: {title[:50]}... (score +20)")

            # Bonus for certain categories
            if section == 'funding':
                base_score = min(100, base_score + 15)  # Funding news is important
            elif section == 'startups':
                base_score = min(100, base_score + 10)

            normalized['importance_score'] = base_score

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing TechCrunch post: {e}")
            return None

    def normalize_comment(self, raw_comment: dict, post_db_id: int) -> Optional[dict]:
        """
        TechCrunch RSS doesn't provide comments

        Returns:
            None (not implemented)
        """
        return None

    def fetch_comments(self, post_id: str, limit: int = 50) -> List[dict]:
        """
        Fetch comments for a post

        Note: TechCrunch RSS doesn't provide comments

        Returns:
            Empty list
        """
        logger.debug("TechCrunch RSS parser doesn't support comments")
        return []

