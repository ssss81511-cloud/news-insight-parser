"""
Reddit Parser - парсинг r/startups, r/SaaS, r/entrepreneur

Особенности:
- Использует публичные Reddit RSS feeds (БЕЗ авторизации!)
- Парсит посты, заголовки, контент
- Детектирует фокус-паттерны ("Is anyone else", "How do you deal with")
- Повышает importance_score для постов с паттернами

НЕ ТРЕБУЕТ API ключей или регистрации приложения!
Reddit RSS feeds работают без ограничений.
"""
import feedparser
import requests
import time
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from parsers.base_parser import BaseParser
from loguru import logger
from html import unescape
from time import mktime


class RedditParser(BaseParser):
    """Parser for Reddit communities using public RSS feeds"""

    # Фокус-паттерны для детекции важных вопросов
    FOCUS_PATTERNS = [
        r"is anyone else",
        r"does anyone else",
        r"how do you deal with",
        r"how do you handle",
        r"what's your experience with",
        r"struggling with",
        r"hard time with",
        r"can't figure out",
        r"need advice on",
        r"looking for advice",
    ]

    # Subreddits для парсинга
    SUBREDDITS = {
        'startups': 'r/startups - стартап-сообщество',
        'SaaS': 'r/SaaS - SaaS продукты и обсуждения',
        'Entrepreneur': 'r/Entrepreneur - предпринимательство',
    }

    # Base URL для Reddit RSS
    BASE_URL = "https://www.reddit.com"

    def __init__(self):
        """Initialize Reddit parser"""
        super().__init__('reddit')

        # User agent для запросов
        self.headers = {
            'User-Agent': 'NewsInsightParser/2.0 (Educational project for startup insights)'
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # 2 секунды между запросами

        logger.info("Reddit RSS parser initialized (no auth required)")

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

    def _extract_score(self, entry: Dict) -> int:
        """Try to extract score from Reddit RSS entry"""
        # В RSS нет прямого score, пытаемся извлечь из категорий
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if 'points' in tag.get('label', '').lower():
                    # Пытаемся извлечь число
                    match = re.search(r'(\d+)\s*points?', tag.get('label', ''))
                    if match:
                        return int(match.group(1))

        # Если не удалось - возвращаем 0
        return 0

    def _extract_comments_count(self, entry: Dict) -> int:
        """Try to extract comments count from Reddit RSS entry"""
        # В RSS может быть в summary или tags
        if hasattr(entry, 'summary'):
            match = re.search(r'(\d+)\s*comments?', entry.summary, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def fetch_posts(self, section: str, limit: int = 50) -> List[Dict]:
        """
        Fetch posts from a subreddit using RSS feed

        Args:
            section: Subreddit name (e.g., 'startups', 'SaaS')
            limit: Number of posts to fetch (RSS обычно возвращает ~25)

        Returns:
            List of raw post dictionaries
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/r/{section}/.rss"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"Failed to fetch RSS: HTTP {response.status_code}")
                return []

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logger.warning(f"No entries found in r/{section} RSS feed")
                return []

            posts = []

            for entry in feed.entries[:limit]:
                # Извлекаем ID из ссылки (последняя часть URL)
                post_id = entry.link.rstrip('/').split('/')[-2] if '/comments/' in entry.link else ''

                # Получаем контент
                content = ''
                if hasattr(entry, 'content') and entry.content:
                    content = self._clean_html(entry.content[0].value)
                elif hasattr(entry, 'summary'):
                    content = self._clean_html(entry.summary)

                # Время создания
                created_utc = 0
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    created_utc = mktime(entry.published_parsed)

                # Автор
                author = entry.author if hasattr(entry, 'author') else '[unknown]'

                post_data = {
                    'id': post_id,
                    'title': entry.title,
                    'selftext': content,
                    'author': author,
                    'score': self._extract_score(entry),
                    'upvote_ratio': 0,  # RSS не предоставляет эту информацию
                    'num_comments': self._extract_comments_count(entry),
                    'created_utc': created_utc,
                    'url': entry.link,
                    'permalink': entry.link,
                    'subreddit': section,
                    'is_self': True,  # Предполагаем что text post
                    'link_flair_text': None,
                }

                posts.append(post_data)

            logger.info(f"Fetched {len(posts)} posts from r/{section} via RSS")
            return posts

        except Exception as e:
            logger.error(f"Error fetching RSS from r/{section}: {e}")
            return []

    def fetch_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetch comments for a post

        ВНИМАНИЕ: RSS feeds не предоставляют комментарии.
        Эта функция возвращает пустой список.

        Для получения комментариев требуется:
        - OAuth авторизация через PRAW
        - Или HTML scraping (не рекомендуется)

        Args:
            post_id: Reddit post ID
            limit: Max number of comments to fetch

        Returns:
            Empty list (RSS не поддерживает комментарии)
        """
        logger.warning("Reddit RSS feeds do not provide comments. Skipping.")
        return []

    def _detect_focus_patterns(self, text: str) -> bool:
        """
        Детектирует наличие фокус-паттернов в тексте

        Args:
            text: Текст для проверки (title + selftext)

        Returns:
            True если найден хотя бы один паттерн
        """
        if not text:
            return False

        text_lower = text.lower()

        for pattern in self.FOCUS_PATTERNS:
            if re.search(pattern, text_lower):
                logger.debug(f"Found focus pattern: {pattern}")
                return True

        return False

    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Convert Reddit post to UniversalPost format

        Args:
            raw_post: Raw Reddit post data from RSS

        Returns:
            Normalized post dictionary
        """
        # Объединяем title и selftext для анализа
        full_text = f"{raw_post['title']} {raw_post.get('selftext', '')}"

        # Детектируем фокус-паттерны
        has_focus_pattern = self._detect_focus_patterns(full_text)

        # Определяем тип поста
        post_type = 'discussion'
        title_lower = raw_post['title'].lower()
        if any(word in title_lower for word in ['question', 'help', 'how to', 'how do']):
            post_type = 'question'
        elif any(word in title_lower for word in ['feedback', 'review', 'roast my']):
            post_type = 'feedback'

        normalized = {
            'source': 'reddit',
            'source_id': raw_post['id'],
            'source_url': raw_post['permalink'],
            'title': raw_post['title'],
            'content': raw_post.get('selftext', ''),
            'author': raw_post['author'],
            'score': raw_post.get('score', 0),
            'comments_count': raw_post['num_comments'],
            'post_type': post_type,
            'metadata': {
                'subreddit': raw_post['subreddit'],
                'upvote_ratio': 0,  # RSS не предоставляет
                'is_self': raw_post.get('is_self', True),
                'flair': None,
                'external_url': None,
                'has_focus_pattern': has_focus_pattern,
                'source_method': 'rss',  # Помечаем что данные из RSS
            },
            'created_at': datetime.fromtimestamp(raw_post['created_utc'], tz=timezone.utc) if raw_post['created_utc'] else datetime.now(timezone.utc),
        }

        # Генерируем content_hash
        normalized['content_hash'] = self.generate_content_hash(
            normalized['title'],
            normalized['content']
        )

        # Рассчитываем importance_score
        base_score = self.calculate_post_importance(normalized)

        # Бонус за фокус-паттерны
        if has_focus_pattern:
            base_score = min(100, base_score + 15)  # +15 баллов, макс 100
            logger.info(f"Focus pattern detected in: {raw_post['title'][:50]}... (score +15)")

        # RSS не предоставляет upvote_ratio, поэтому бонус не применяем

        normalized['importance_score'] = base_score

        return normalized

    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Convert Reddit comment to UniversalComment format

        ВНИМАНИЕ: RSS не предоставляет комментарии.
        Эта функция не используется при парсинге через RSS.

        Args:
            raw_comment: Raw Reddit comment data
            post_db_id: Database ID of the parent post

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
            'created_at': datetime.fromtimestamp(raw_comment['created_utc'], tz=timezone.utc) if 'created_utc' in raw_comment else datetime.now(timezone.utc),
        }

        return normalized

    def get_available_sections(self) -> List[str]:
        """Get list of available subreddits"""
        return list(self.SUBREDDITS.keys())
