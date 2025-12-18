"""
VC Blogs Parser - парсинг блогов топ венчурных фондов

Особенности:
- Парсит Y Combinator, Sequoia, a16z Future через RSS
- Фокус на: funding advice, market trends, growth strategies
- Детектирует ключевые темы для стартапов
- Повышает importance_score для стратегических инсайтов

НЕ ТРЕБУЕТ авторизации - все через публичные RSS feeds!
"""
import feedparser
import requests
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from parsers.base_parser import BaseParser
from loguru import logger
from html import unescape
from time import mktime


class VCBlogsParser(BaseParser):
    """Parser for VC blogs using RSS feeds"""

    # Фокус-темы для VC инсайтов
    FOCUS_THEMES = [
        r"fundraising",
        r"series\s+[abc]",
        r"venture\s+capital",
        r"go[- ]to[- ]market",
        r"gtm",
        r"product[- ]market\s+fit",
        r"unit\s+economics",
        r"burn\s+rate",
        r"runway",
        r"valuation",
        r"cap\s+table",
        r"term\s+sheet",
        r"hiring",
        r"scaling",
        r"market\s+size",
        r"tam",
        r"competitive\s+advantage",
        r"moat",
    ]

    # VC Blogs конфигурация
    VC_BLOGS = {
        'yc': {
            'name': 'Y Combinator',
            'feed_url': 'https://www.ycombinator.com/blog/feed',
            'description': 'YC Blog - success stories, advice, portfolio news'
        },
        'sequoia': {
            'name': 'Sequoia Capital',
            'feed_url': 'https://www.sequoiacap.com/feed/',
            'description': 'Sequoia - investment insights, portfolio spotlights'
        },
        'a16z': {
            'name': 'a16z Future',
            'feed_url': 'https://future.com/feed/',
            'description': 'a16z Future - tech trends, future of startups'
        },
    }

    def __init__(self):
        """Initialize VC Blogs parser"""
        super().__init__('vc_blogs')

        # User agent для запросов
        self.headers = {
            'User-Agent': 'NewsInsightParser/2.0 (Educational project for startup insights)'
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # 2 секунды между запросами

        logger.info("VC Blogs RSS parser initialized (no auth required)")

    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _clean_html(self, html_text: str) -> str:
        """Remove HTML tags and decode HTML entities"""
        if not html_text:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_text)
        # Decode HTML entities
        text = unescape(text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _detect_focus_themes(self, text: str) -> bool:
        """
        Детектирует наличие фокус-тем в тексте

        Args:
            text: Текст для проверки (title + description)

        Returns:
            True если найдена хотя бы одна тема
        """
        if not text:
            return False

        text_lower = text.lower()

        for theme in self.FOCUS_THEMES:
            if re.search(theme, text_lower):
                logger.debug(f"Found focus theme: {theme}")
                return True

        return False

    def fetch_posts(self, section: str, limit: int = 20) -> List[Dict]:
        """
        Fetch articles from a VC blog

        Args:
            section: Blog identifier (e.g., 'yc', 'sequoia', 'a16z')
            limit: Number of articles to fetch

        Returns:
            List of raw article dictionaries
        """
        if section not in self.VC_BLOGS:
            logger.error(f"Unknown VC blog: {section}")
            return []

        self._rate_limit()

        blog_config = self.VC_BLOGS[section]
        feed_url = blog_config['feed_url']

        try:
            response = requests.get(feed_url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"Failed to fetch RSS from {blog_config['name']}: HTTP {response.status_code}")
                return []

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"No entries found in {blog_config['name']} RSS feed")
                return []

            articles = []

            for entry in feed.entries[:limit]:
                # Извлекаем ID из ссылки
                article_id = entry.link.rstrip('/').split('/')[-1] if '/' in entry.link else entry.link

                # Получаем контент/описание
                description = ''
                if hasattr(entry, 'summary') and entry.summary:
                    description = self._clean_html(entry.summary)
                elif hasattr(entry, 'description') and entry.description:
                    description = self._clean_html(entry.description)

                # Время создания
                created_utc = 0
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    created_utc = mktime(entry.published_parsed)

                # Автор (если есть)
                author = entry.author if hasattr(entry, 'author') else blog_config['name']

                article_data = {
                    'id': article_id,
                    'title': entry.title,
                    'description': description,
                    'author': author,
                    'url': entry.link,
                    'created_utc': created_utc,
                    'blog_name': blog_config['name'],
                    'blog_id': section,
                }

                articles.append(article_data)

            logger.info(f"Fetched {len(articles)} articles from {blog_config['name']} via RSS")
            return articles

        except Exception as e:
            logger.error(f"Error fetching RSS from {blog_config['name']}: {e}")
            return []

    def fetch_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetch comments for an article

        ВНИМАНИЕ: VC blogs RSS feeds не предоставляют комментарии.

        Args:
            post_id: Article ID
            limit: Max number of comments

        Returns:
            Empty list (не поддерживается)
        """
        logger.warning("VC blogs RSS feeds do not provide comments. Skipping.")
        return []

    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Convert VC blog article to UniversalPost format

        Args:
            raw_post: Raw article data from RSS

        Returns:
            Normalized post dictionary
        """
        # Объединяем title и description для анализа
        full_text = f"{raw_post['title']} {raw_post.get('description', '')}"

        # Детектируем фокус-темы
        has_focus_theme = self._detect_focus_themes(full_text)

        # Определяем тип
        post_type = 'vc_insight'
        title_lower = raw_post['title'].lower()

        if any(word in title_lower for word in ['partnering with', 'investment in', 'portfolio']):
            post_type = 'portfolio_news'
        elif any(word in title_lower for word in ['how to', 'guide', 'framework']):
            post_type = 'advice'
        elif any(word in title_lower for word in ['trend', 'future', 'market']):
            post_type = 'market_analysis'

        normalized = {
            'source': 'vc_blogs',
            'source_id': raw_post['id'],
            'source_url': raw_post['url'],
            'title': raw_post['title'],
            'content': raw_post.get('description', ''),
            'author': raw_post['author'],
            'score': 0,  # RSS не предоставляет
            'comments_count': 0,  # RSS не предоставляет
            'post_type': post_type,
            'metadata': {
                'blog_name': raw_post['blog_name'],
                'blog_id': raw_post['blog_id'],
                'has_focus_theme': has_focus_theme,
                'source_method': 'rss',
            },
            'created_at': datetime.fromtimestamp(raw_post['created_utc']) if raw_post['created_utc'] else datetime.utcnow(),
        }

        # Генерируем content_hash
        normalized['content_hash'] = self.generate_content_hash(
            normalized['title'],
            normalized['content']
        )

        # Рассчитываем importance_score
        base_score = self.calculate_post_importance(normalized)

        # Бонус за фокус-темы (VC инсайты очень ценны!)
        if has_focus_theme:
            base_score = min(100, base_score + 25)  # +25 баллов для VC инсайтов
            logger.info(f"Focus theme detected in: {raw_post['title'][:50]}... (score +25)")

        # Бонус за VC источник (авторитет)
        base_score = min(100, base_score + 10)  # VC blogs = высокое качество

        normalized['importance_score'] = base_score

        return normalized

    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Convert comment to UniversalComment format

        ВНИМАНИЕ: VC blogs не поддерживают комментарии через RSS.

        Args:
            raw_comment: Raw comment data
            post_db_id: Database ID of the parent post

        Returns:
            Normalized comment dictionary
        """
        normalized = {
            'post_id': post_db_id,
            'source_comment_id': raw_comment.get('id', ''),
            'author': raw_comment.get('author', '[unknown]'),
            'content': raw_comment.get('body', ''),
            'score': 0,
            'parent_comment_id': None,
            'is_op': False,
            'created_at': datetime.utcnow(),
        }

        return normalized

    def get_available_sections(self) -> List[str]:
        """Get list of available VC blogs"""
        return list(self.VC_BLOGS.keys())
