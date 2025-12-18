"""
Dev.to Parser - парсинг статей про стартапы и entrepreneurship

Особенности:
- Использует публичный Dev.to API (БЕЗ авторизации!)
- Парсит статьи по тегам: startup, entrepreneur, saas, buildinpublic
- Детектирует фокус-темы (growth, revenue, problems, solutions)
- Повышает importance_score для релевантных статей

НЕ ТРЕБУЕТ API ключей!
Dev.to API доступен публично для чтения.
"""
import requests
import time
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from parsers.base_parser import BaseParser
from loguru import logger


class DevToParser(BaseParser):
    """Parser for Dev.to articles using public API"""

    # Фокус-темы для приоритизации статей
    FOCUS_THEMES = [
        r"revenue",
        r"mrr",
        r"arr",
        r"growth\s+hack",
        r"user\s+acquisition",
        r"conversion",
        r"retention",
        r"churn",
        r"product[- ]market\s+fit",
        r"mvp",
        r"launch",
        r"failed?",
        r"lesson[s]?\s+learned",
        r"mistake[s]?",
        r"build\s+in\s+public",
    ]

    # Теги для парсинга
    TAGS = {
        'startup': 'Startup - стартапы и launch истории',
        'entrepreneur': 'Entrepreneur - предпринимательство',
        'saas': 'SaaS - SaaS продукты и рост',
        'buildinpublic': 'Building in Public - открытая разработка',
        'indiehacker': 'Indie Hacker - независимые разработчики',
    }

    # Base URL для Dev.to API
    BASE_URL = "https://dev.to/api"

    def __init__(self):
        """Initialize Dev.to parser"""
        super().__init__('devto')

        # User agent для запросов
        self.headers = {
            'User-Agent': 'NewsInsightParser/2.0 (Educational project for startup insights)'
        }

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1  # 1 секунда между запросами

        logger.info("Dev.to API parser initialized (no auth required)")

    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

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

    def fetch_posts(self, section: str, limit: int = 30) -> List[Dict]:
        """
        Fetch articles from Dev.to API by tag

        Args:
            section: Tag name (e.g., 'startup', 'saas')
            limit: Number of articles to fetch (max 1000 per request)

        Returns:
            List of raw article dictionaries
        """
        self._rate_limit()

        # Dev.to API endpoint
        url = f"{self.BASE_URL}/articles"
        params = {
            'tag': section,
            'per_page': min(limit, 100),  # API max is 1000, но используем 100
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"Dev.to API returned {response.status_code}")
                return []

            articles = response.json()

            if not articles:
                logger.warning(f"No articles found for tag: {section}")
                return []

            # Нормализуем данные для совместимости
            normalized_articles = []

            for article in articles:
                normalized_article = {
                    'id': str(article['id']),
                    'title': article['title'],
                    'description': article.get('description', ''),
                    'author': article['user']['name'],
                    'author_username': article['user']['username'],
                    'tags': article.get('tag_list', []),
                    'reactions': article.get('positive_reactions_count', 0),
                    'comments': article.get('comments_count', 0),
                    'url': article['url'],
                    'published_at': article.get('published_at'),
                    'cover_image': article.get('cover_image'),
                }

                normalized_articles.append(normalized_article)

            logger.info(f"Fetched {len(normalized_articles)} articles for tag #{section}")
            return normalized_articles

        except Exception as e:
            logger.error(f"Error fetching articles for tag {section}: {e}")
            return []

    def fetch_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """
        Fetch comments for an article

        Dev.to API provides comments endpoint: /api/comments?a_id={article_id}

        Args:
            post_id: Dev.to article ID
            limit: Max number of comments to fetch

        Returns:
            List of raw comment dictionaries
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/comments"
        params = {'a_id': post_id}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"Dev.to API returned {response.status_code} for comments")
                return []

            comments = response.json()

            # Нормализуем комментарии
            normalized_comments = []

            for comment in comments[:limit]:
                normalized_comment = {
                    'id': str(comment['id_code']),
                    'body': comment.get('body_html', ''),  # HTML контент
                    'author': comment['user']['name'],
                    'created_at': comment['created_at'],
                }

                normalized_comments.append(normalized_comment)

            logger.info(f"Fetched {len(normalized_comments)} comments for article {post_id}")
            return normalized_comments

        except Exception as e:
            logger.error(f"Error fetching comments for article {post_id}: {e}")
            return []

    def normalize_post(self, raw_post: Dict) -> Dict:
        """
        Convert Dev.to article to UniversalPost format

        Args:
            raw_post: Raw Dev.to article data

        Returns:
            Normalized post dictionary
        """
        # Объединяем title и description для анализа
        full_text = f"{raw_post['title']} {raw_post.get('description', '')}"

        # Детектируем фокус-темы
        has_focus_theme = self._detect_focus_themes(full_text)

        # Определяем тип
        post_type = 'article'
        title_lower = raw_post['title'].lower()

        if any(word in title_lower for word in ['how to', 'how i', 'tutorial', 'guide']):
            post_type = 'tutorial'
        elif any(word in title_lower for word in ['lesson', 'mistake', 'failed', 'failure']):
            post_type = 'case_study'
        elif 'launch' in title_lower or 'released' in title_lower:
            post_type = 'announcement'

        # Парсим дату
        created_at = datetime.now(timezone.utc)
        if raw_post.get('published_at'):
            try:
                created_at = datetime.fromisoformat(raw_post['published_at'].replace('Z', '+00:00'))
            except:
                pass

        normalized = {
            'source': 'devto',
            'source_id': raw_post['id'],
            'source_url': raw_post['url'],
            'title': raw_post['title'],
            'content': raw_post.get('description', ''),
            'author': raw_post['author'],
            'score': raw_post.get('reactions', 0),
            'comments_count': raw_post.get('comments', 0),
            'post_type': post_type,
            'metadata': {
                'author_username': raw_post.get('author_username'),
                'tags': raw_post.get('tags', []),
                'cover_image': raw_post.get('cover_image'),
                'has_focus_theme': has_focus_theme,
                'source_method': 'api',
            },
            'created_at': created_at,
        }

        # Генерируем content_hash
        normalized['content_hash'] = self.generate_content_hash(
            normalized['title'],
            normalized['content']
        )

        # Рассчитываем importance_score
        base_score = self.calculate_post_importance(normalized)

        # Бонус за фокус-темы
        if has_focus_theme:
            base_score = min(100, base_score + 15)  # +15 баллов
            logger.info(f"Focus theme detected in: {raw_post['title'][:50]}... (score +15)")

        # Бонус за высокие reactions (популярный контент)
        reactions = raw_post.get('reactions', 0)
        if reactions > 50:
            base_score = min(100, base_score + 10)
        elif reactions > 100:
            base_score = min(100, base_score + 15)

        normalized['importance_score'] = base_score

        return normalized

    def normalize_comment(self, raw_comment: Dict, post_db_id: int) -> Dict:
        """
        Convert Dev.to comment to UniversalComment format

        Args:
            raw_comment: Raw Dev.to comment data
            post_db_id: Database ID of the parent article

        Returns:
            Normalized comment dictionary
        """
        # Парсим дату
        created_at = datetime.now(timezone.utc)
        if raw_comment.get('created_at'):
            try:
                created_at = datetime.fromisoformat(raw_comment['created_at'].replace('Z', '+00:00'))
            except:
                pass

        normalized = {
            'post_id': post_db_id,
            'source_comment_id': raw_comment['id'],
            'author': raw_comment['author'],
            'content': raw_comment.get('body', ''),
            'score': 0,  # Dev.to API не предоставляет score для комментариев
            'parent_comment_id': None,  # Упрощаем - без nested threading
            'is_op': False,  # Нужна дополнительная логика для определения
            'created_at': created_at,
        }

        return normalized

    def get_available_sections(self) -> List[str]:
        """Get list of available tags"""
        return list(self.TAGS.keys())
