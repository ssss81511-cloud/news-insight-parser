"""
Base parser class - unified interface for all data sources
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timezone
import hashlib


class BaseParser(ABC):
    """
    Abstract base class for all parsers

    All parsers (HN, Reddit, Product Hunt, etc.) must inherit from this class
    and implement the required methods.
    """

    def __init__(self, source_name: str):
        """
        Initialize parser

        Args:
            source_name: Unique identifier for this source (e.g., 'hacker_news', 'reddit')
        """
        self.source_name = source_name
        self.rate_limit_delay = 1  # Default delay between requests

    @abstractmethod
    def fetch_posts(self, section: str, limit: int = 20) -> List[Dict]:
        """
        Fetch posts from the source

        Args:
            section: Section to fetch from (e.g., 'ask_hn', 'show_hn' for HN)
            limit: Maximum number of posts to fetch

        Returns:
            List of raw posts in source-specific format
        """
        pass

    @abstractmethod
    def fetch_comments(self, post_id: str, limit: int = 10) -> List[Dict]:
        """
        Fetch comments for a specific post

        Args:
            post_id: ID of the post in the source system
            limit: Maximum number of comments to fetch

        Returns:
            List of raw comments in source-specific format
        """
        pass

    @abstractmethod
    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Normalize source-specific post format to universal format

        Args:
            raw_post: Raw post data from the source

        Returns:
            Normalized post in UniversalPost format
        """
        pass

    @abstractmethod
    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Normalize source-specific comment format to universal format

        Args:
            raw_comment: Raw comment data from the source
            post_db_id: Database ID of the parent post

        Returns:
            Normalized comment in UniversalComment format
        """
        pass

    def generate_content_hash(self, title: str, content: str) -> str:
        """
        Generate unique hash for content to detect duplicates

        Uses title + content to create fingerprint.
        Similar content from different sources will have similar hashes.

        Args:
            title: Post title
            content: Post content

        Returns:
            SHA-256 hash of normalized content
        """
        # Normalize text: lowercase, strip whitespace
        normalized = f"{title.lower().strip()} {content.lower().strip() if content else ''}"

        # Generate hash
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract keywords from text

        Args:
            text: Text to extract keywords from
            min_length: Minimum word length

        Returns:
            List of keywords
        """
        import re

        # Remove special characters and convert to lowercase
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Split into words and filter
        words = [w for w in clean_text.split() if len(w) >= min_length]

        # Remove common stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'was', 'with', 'this', 'that', 'from', 'have', 'has', 'had',
            'been', 'were', 'will', 'would', 'could', 'should', 'may', 'might'
        }

        return [w for w in words if w not in stopwords]

    def calculate_post_importance(self, post_data: Dict) -> float:
        """
        Calculate importance score for a post

        Factors:
        - Engagement (score/upvotes)
        - Comments count
        - Recency
        - Author reputation (if available)

        Args:
            post_data: Normalized post data

        Returns:
            Importance score (0-100)
        """
        score = 0.0

        # Factor 1: Engagement (40% weight)
        engagement = post_data.get('score', 0)
        score += min(engagement / 10, 40)  # Cap at 40 points

        # Factor 2: Comments (30% weight)
        comments = post_data.get('comments_count', 0)
        score += min(comments / 2, 30)  # Cap at 30 points

        # Factor 3: Recency (30% weight)
        created_at = post_data.get('created_at')
        if created_at:
            hours_old = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            # Fresh content gets more points
            recency_score = max(0, 30 - (hours_old / 24))
            score += recency_score

        return min(score, 100)  # Cap at 100

    def parse_and_save(self, db_manager, section: str, limit: int = 20) -> int:
        """
        Parse posts and save to database

        Args:
            db_manager: DatabaseManager instance
            section: Section to parse
            limit: Number of posts to fetch

        Returns:
            Number of items saved
        """
        # Start tracking
        run = db_manager.start_parser_run(self.source_name, section)
        items_saved = 0

        # Cutoff date - don't save posts older than 2 months
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=60)

        try:
            # Fetch posts
            raw_posts = self.fetch_posts(section, limit)

            for raw_post in raw_posts:
                # Normalize
                normalized = self.normalize_post(raw_post)

                # Skip if post is too old (older than 2 months)
                post_date = normalized.get('created_at')
                if post_date and post_date < cutoff_date:
                    continue  # Skip old post

                # Generate content hash
                normalized['content_hash'] = self.generate_content_hash(
                    normalized['title'],
                    normalized.get('content', '')
                )

                # Calculate importance
                normalized['importance_score'] = self.calculate_post_importance(normalized)

                # Save to DB
                db_post = db_manager.add_universal_post(normalized)

                # Fetch and save comments if needed
                if section in ['ask_hn', 'show_hn', 'ask', 'show', 'discussion']:
                    raw_comments = self.fetch_comments(
                        normalized['source_id'],
                        limit=10
                    )

                    for raw_comment in raw_comments:
                        normalized_comment = self.normalize_comment(raw_comment, db_post.id)
                        db_manager.add_universal_comment(normalized_comment)

                items_saved += 1

            # Mark as success
            db_manager.finish_parser_run(run.id, items_saved, 'success')

        except Exception as e:
            # Mark as failed
            db_manager.finish_parser_run(run.id, items_saved, 'failed', str(e))
            raise

        return items_saved

    def get_available_sections(self) -> List[str]:
        """
        Get list of available sections for this source

        Returns:
            List of section names
        """
        return []
