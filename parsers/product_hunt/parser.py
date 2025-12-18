"""
Product Hunt Parser - парсинг ежедневных запусков продуктов

Особенности:
- Использует публичный Product Hunt RSS feed (БЕЗ авторизации!)
- Парсит новые продукты, makers, описания
- Детектирует фокус-категории (SaaS, B2B, AI, Productivity)
- Повышает importance_score для релевантных продуктов

НЕ ТРЕБУЕТ API ключей или регистрации!
Product Hunt RSS feed работает без ограничений.
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


class ProductHuntParser(BaseParser):
    """Parser for Product Hunt daily launches using public RSS feed"""

    # Фокус-категории для приоритизации продуктов
    FOCUS_CATEGORIES = [
        r"saas",
        r"b2b",
        r"productivity",
        r"analytics",
        r"automation",
        r"ai\s+powered",
        r"artificial intelligence",
        r"crm",
        r"dashboard",
        r"startup\s+tools?",
        r"developer\s+tools?",
        r"no[- ]?code",
        r"low[- ]?code",
    ]

    # Base URL для Product Hunt RSS
    BASE_URL = "https://www.producthunt.com"

    def __init__(self):
        """Initialize Product Hunt parser"""
        super().__init__('product_hunt')

        # User agent для запросов
        self.headers = {
            'User-Agent': 'NewsInsightParser/2.0 (Educational project for startup insights)'
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # 2 секунды между запросами

        logger.info("Product Hunt RSS parser initialized (no auth required)")

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

    def _detect_focus_categories(self, text: str) -> bool:
        """
        Детектирует наличие фокус-категорий в тексте

        Args:
            text: Текст для проверки (title + description)

        Returns:
            True если найдена хотя бы одна категория
        """
        if not text:
            return False

        text_lower = text.lower()

        for category in self.FOCUS_CATEGORIES:
            if re.search(category, text_lower):
                logger.debug(f"Found focus category: {category}")
                return True

        return False

    def fetch_posts(self, section: str = 'daily', limit: int = 50) -> List[Dict]:
        """
        Fetch products from Product Hunt RSS feed

        Args:
            section: Not used for Product Hunt (single feed)
            limit: Number of products to fetch

        Returns:
            List of raw product dictionaries
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/feed"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"Failed to fetch RSS: HTTP {response.status_code}")
                return []

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning("No entries found in Product Hunt RSS feed")
                return []

            products = []

            for entry in feed.entries[:limit]:
                # Извлекаем ID из ссылки
                product_id = entry.link.rstrip('/').split('/')[-1] if '/' in entry.link else ''

                # Получаем описание
                description = ''
                if hasattr(entry, 'summary') and entry.summary:
                    description = self._clean_html(entry.summary)

                # Время создания
                created_utc = 0
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    created_utc = mktime(entry.published_parsed)

                # Maker/автор
                maker = entry.author if hasattr(entry, 'author') else '[unknown]'

                product_data = {
                    'id': product_id,
                    'title': entry.title,
                    'description': description,
                    'maker': maker,
                    'url': entry.link,
                    'created_utc': created_utc,
                }

                products.append(product_data)

            logger.info(f"Fetched {len(products)} products from Product Hunt via RSS")
            return products

        except Exception as e:
            logger.error(f"Error fetching RSS from Product Hunt: {e}")
            return []

    def fetch_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetch comments for a product

        ВНИМАНИЕ: RSS feeds не предоставляют комментарии.
        Эта функция возвращает пустой список.

        Args:
            post_id: Product Hunt product ID
            limit: Max number of comments to fetch

        Returns:
            Empty list (RSS не поддерживает комментарии)
        """
        logger.warning("Product Hunt RSS feeds do not provide comments. Skipping.")
        return []

    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Convert Product Hunt product to UniversalPost format

        Args:
            raw_post: Raw Product Hunt product data from RSS

        Returns:
            Normalized post dictionary
        """
        # Объединяем title и description для анализа
        full_text = f"{raw_post['title']} {raw_post.get('description', '')}"

        # Детектируем фокус-категории
        has_focus_category = self._detect_focus_categories(full_text)

        # Определяем тип (для Product Hunt все - это launches)
        post_type = 'product_launch'

        normalized = {
            'source': 'product_hunt',
            'source_id': raw_post['id'],
            'source_url': raw_post['url'],
            'title': raw_post['title'],
            'content': raw_post.get('description', ''),
            'author': raw_post['maker'],
            'score': 0,  # RSS не предоставляет upvotes
            'comments_count': 0,  # RSS не предоставляет
            'post_type': post_type,
            'metadata': {
                'maker': raw_post['maker'],
                'has_focus_category': has_focus_category,
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

        # Бонус за фокус-категории
        if has_focus_category:
            base_score = min(100, base_score + 20)  # +20 баллов для релевантных продуктов
            logger.info(f"Focus category detected in: {raw_post['title'][:50]}... (score +20)")

        normalized['importance_score'] = base_score

        return normalized

    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Convert Product Hunt comment to UniversalComment format

        ВНИМАНИЕ: RSS не предоставляет комментарии.
        Эта функция не используется при парсинге через RSS.

        Args:
            raw_comment: Raw Product Hunt comment data
            post_db_id: Database ID of the parent product

        Returns:
            Normalized comment dictionary
        """
        normalized = {
            'post_id': post_db_id,
            'source_comment_id': raw_comment.get('id', ''),
            'author': raw_comment.get('author', '[unknown]'),
            'content': raw_comment.get('body', ''),
            'score': raw_comment.get('score', 0),
            'parent_comment_id': raw_comment.get('parent_id'),
            'is_op': raw_comment.get('is_submitter', False),
            'created_at': datetime.fromtimestamp(raw_comment['created_utc']) if 'created_utc' in raw_comment else datetime.utcnow(),
        }

        return normalized

    def get_available_sections(self) -> List[str]:
        """Get list of available sections (Product Hunt has only one feed)"""
        return ['daily']  # Один feed - ежедневные запуски
