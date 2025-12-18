"""
Refactored Hacker News parser using BaseParser architecture
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from parsers.base_parser import BaseParser


class HackerNewsParser(BaseParser):
    """
    Hacker News parser using Firebase API
    Inherits from BaseParser for unified interface
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    # Section mapping
    SECTIONS = {
        'ask_hn': 'askstories',
        'show_hn': 'showstories',
        'new': 'newstories'
    }

    def __init__(self):
        """Initialize HN parser"""
        super().__init__('hacker_news')
        self.session = requests.Session()
        self.rate_limit_delay = 1  # 1 second between requests

    def _make_request(self, endpoint: str) -> Optional[dict]:
        """Make API request with rate limiting"""
        url = f"{self.BASE_URL}/{endpoint}.json"
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def get_item(self, item_id: int) -> Optional[Dict]:
        """Get item (post/comment) by ID"""
        return self._make_request(f"item/{item_id}")

    def fetch_posts(self, section: str, limit: int = 20) -> List[Dict]:
        """
        Fetch posts from HN section

        Args:
            section: 'ask_hn', 'show_hn', or 'new'
            limit: Maximum number of posts

        Returns:
            List of raw HN posts
        """
        # Get endpoint for section
        endpoint = self.SECTIONS.get(section)
        if not endpoint:
            logger.error(f"Unknown section: {section}")
            return []

        # Fetch story IDs
        story_ids = self._make_request(endpoint)
        if not story_ids:
            return []

        # Fetch individual stories
        stories = []
        for story_id in story_ids[:limit]:
            item = self.get_item(story_id)
            if item and item.get('type') == 'story':
                # Add section type
                item['post_type'] = section

                # Filter for Ask/Show HN
                title = item.get('title', '').lower()
                if section == 'ask_hn' and 'ask hn' not in title:
                    continue
                if section == 'show_hn' and 'show hn' not in title:
                    continue

                stories.append(item)

        logger.info(f"Fetched {len(stories)} posts from {section}")
        return stories

    def fetch_comments(self, post_id: str, limit: int = 10) -> List[Dict]:
        """
        Fetch comments for a post

        Args:
            post_id: HN item ID (as string for compatibility)
            limit: Maximum number of comments

        Returns:
            List of raw HN comments
        """
        story = self.get_item(int(post_id))
        if not story or 'kids' not in story:
            return []

        comments = []
        comment_ids = story.get('kids', [])[:limit]

        for comment_id in comment_ids:
            comment = self.get_item(comment_id)
            if comment and comment.get('type') == 'comment' and comment.get('text'):
                comments.append(comment)

        return comments

    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Normalize HN post to UniversalPost format

        Args:
            raw_post: Raw HN item

        Returns:
            Normalized post in UniversalPost format
        """
        hn_id = raw_post.get('id')

        return {
            # Source identification
            'source': 'hacker_news',
            'source_id': str(hn_id),
            'source_url': f"https://news.ycombinator.com/item?id={hn_id}",

            # Content
            'title': raw_post.get('title', ''),
            'content': raw_post.get('text'),  # Self-post text if any
            'author': raw_post.get('by', 'unknown'),

            # Engagement
            'score': raw_post.get('score', 0),
            'comments_count': len(raw_post.get('kids', [])),

            # Classification
            'post_type': raw_post.get('post_type', 'new'),
            'category': None,  # HN doesn't have categories

            # Temporal
            'created_at': datetime.fromtimestamp(raw_post.get('time', 0)),
        }

    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Normalize HN comment to UniversalComment format

        Args:
            raw_comment: Raw HN comment
            post_db_id: Database ID of parent post

        Returns:
            Normalized comment in UniversalComment format
        """
        return {
            # Source identification
            'source': 'hacker_news',
            'source_id': str(raw_comment.get('id')),

            # Relationship
            'post_id': post_db_id,
            'parent_id': raw_comment.get('parent'),

            # Content
            'author': raw_comment.get('by', 'unknown'),
            'content': raw_comment.get('text', ''),

            # Engagement
            'score': 0,  # HN doesn't provide comment scores via API

            # Temporal
            'created_at': datetime.fromtimestamp(raw_comment.get('time', 0)),
        }

    def get_available_sections(self) -> List[str]:
        """Get list of available HN sections"""
        return list(self.SECTIONS.keys())


# Convenience function for backward compatibility
def create_hn_parser():
    """Create and return HN parser instance"""
    return HackerNewsParser()
