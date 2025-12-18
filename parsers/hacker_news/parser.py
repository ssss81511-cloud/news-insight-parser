"""
Hacker News parser using official Firebase API
https://github.com/HackerNews/API
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger


class HackerNewsParser:
    """Parser for Hacker News using Firebase API"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, rate_limit_delay: int = 1):
        """
        Initialize HN parser

        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()

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

    def get_new_stories(self, limit: int = 30) -> List[Dict]:
        """Get new stories"""
        story_ids = self._make_request("newstories")
        if not story_ids:
            return []

        stories = []
        for story_id in story_ids[:limit]:
            item = self.get_item(story_id)
            if item and item.get('type') == 'story':
                item['post_type'] = 'new'
                stories.append(item)

        return stories

    def get_ask_hn(self, limit: int = 30) -> List[Dict]:
        """
        Get Ask HN posts
        Focus: Questions from founders and developers
        """
        story_ids = self._make_request("askstories")
        if not story_ids:
            return []

        stories = []
        for story_id in story_ids[:limit]:
            item = self.get_item(story_id)
            if item and item.get('type') == 'story':
                # Filter for Ask HN
                title = item.get('title', '').lower()
                if 'ask hn' in title:
                    item['post_type'] = 'ask_hn'
                    stories.append(item)

        return stories

    def get_show_hn(self, limit: int = 30) -> List[Dict]:
        """
        Get Show HN posts
        Focus: New products, early launches, feedback requests
        """
        story_ids = self._make_request("showstories")
        if not story_ids:
            return []

        stories = []
        for story_id in story_ids[:limit]:
            item = self.get_item(story_id)
            if item and item.get('type') == 'story':
                # Filter for Show HN
                title = item.get('title', '').lower()
                if 'show hn' in title:
                    item['post_type'] = 'show_hn'
                    stories.append(item)

        return stories

    def get_comments(self, story_id: int, limit: int = 50) -> List[Dict]:
        """
        Get comments for a story
        Focus: Early feedback and discussions
        """
        story = self.get_item(story_id)
        if not story or 'kids' not in story:
            return []

        comments = []
        comment_ids = story.get('kids', [])[:limit]

        for comment_id in comment_ids:
            comment = self.get_item(comment_id)
            if comment and comment.get('type') == 'comment':
                # Get text content
                if comment.get('text'):
                    comments.append(comment)

        return comments

    @staticmethod
    def normalize_post(item: Dict) -> Dict:
        """Normalize HN item to our database format"""
        return {
            'hn_id': item.get('id'),
            'title': item.get('title', ''),
            'url': item.get('url'),
            'text': item.get('text'),
            'author': item.get('by', 'unknown'),
            'score': item.get('score', 0),
            'post_type': item.get('post_type', 'new'),
            'created_at': datetime.fromtimestamp(item.get('time', 0)),
            'comments_count': len(item.get('kids', []))
        }

    @staticmethod
    def normalize_comment(item: Dict, post_db_id: int) -> Dict:
        """Normalize HN comment to our database format"""
        return {
            'hn_id': item.get('id'),
            'post_id': post_db_id,
            'parent_id': item.get('parent'),
            'author': item.get('by', 'unknown'),
            'text': item.get('text', ''),
            'created_at': datetime.fromtimestamp(item.get('time', 0))
        }

    def parse_all_sections(self, limit_per_section: int = 20) -> Dict[str, List[Dict]]:
        """
        Parse all HN sections: Ask HN, Show HN, New

        Returns:
            Dict with keys: 'ask_hn', 'show_hn', 'new'
        """
        logger.info("Starting HN parsing...")

        results = {
            'ask_hn': self.get_ask_hn(limit=limit_per_section),
            'show_hn': self.get_show_hn(limit=limit_per_section),
            'new': self.get_new_stories(limit=limit_per_section)
        }

        logger.info(f"Parsed: {len(results['ask_hn'])} Ask HN, "
                   f"{len(results['show_hn'])} Show HN, "
                   f"{len(results['new'])} New stories")

        return results
