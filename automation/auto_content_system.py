"""
Auto Content System - Main Orchestrator

Coordinates all automation components to provide end-to-end automated
content generation and posting workflow.
"""
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import json
import traceback

from storage.universal_database import UniversalDatabaseManager
from storage.universal_models import UniversalPost
from automation.topic_selector import TopicSelector
from automation.telegram_poster import TelegramPoster
from automation.reel_generator import create_reel_generator
from analyzers.content_generator import ContentGenerator


class AutoContentSystem:
    """
    Main orchestrator for automated content generation and posting

    Workflow:
    1. Select unique topic (TopicSelector)
    2. Get posts for topic (Database)
    3. Generate content (ContentGenerator)
    4. Save content to database
    5. Mark topic as used
    6. Generate reel image (ReelGenerator)
    7. Post to Telegram (TelegramPoster)
    8. Mark content as published

    Features:
    - End-to-end automation
    - Comprehensive error handling
    - Detailed logging
    - Status tracking
    - Retry logic
    - Graceful degradation
    """

    def __init__(
        self,
        db_manager: UniversalDatabaseManager,
        content_generator: ContentGenerator,
        topic_selector: TopicSelector,
        telegram_poster: Optional[TelegramPoster] = None,
        reel_generator = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize AutoContentSystem

        Args:
            db_manager: Database manager instance
            content_generator: Content generator instance
            topic_selector: Topic selector instance
            telegram_poster: Telegram poster instance (optional)
            reel_generator: Reel generator instance (optional)
            config: Configuration dictionary with defaults:
                {
                    'topic_exclude_days': 30,
                    'topic_prefer_trending': True,
                    'topic_min_posts': 3,
                    'content_format': 'long_post',
                    'content_language': 'ru',
                    'content_tone': 'professional',
                    'reel_aspect_ratio': 'reel',
                    'reel_style': 'modern',
                    'enable_reel': True,
                    'enable_telegram': True,
                    'max_retries': 3
                }
        """
        self.db = db_manager
        self.content_generator = content_generator
        self.topic_selector = topic_selector
        self.telegram_poster = telegram_poster
        self.reel_generator = reel_generator or create_reel_generator()

        # Default configuration
        self.config = {
            'topic_exclude_days': 30,
            'topic_prefer_trending': True,
            'topic_min_posts': 3,
            'content_format': 'long_post',
            'content_language': 'ru',
            'content_tone': 'professional',
            'reel_aspect_ratio': 'reel',
            'reel_style': 'modern',
            'enable_reel': True,
            'enable_telegram': True,
            'max_retries': 3
        }

        # Override with provided config
        if config:
            self.config.update(config)

        print(f"[AUTO CONTENT SYSTEM] Initialized", flush=True)
        print(f"[AUTO CONTENT SYSTEM] Config: {self.config}", flush=True)

    async def generate_and_post(self) -> Dict:
        """
        Main workflow: Generate content and post to Telegram

        This is the primary method that orchestrates the entire workflow.

        Returns:
            Dict with execution result:
            {
                'success': bool,
                'content_id': int or None,
                'message_id': int or None,
                'image_path': str or None,
                'topic': Dict or None,
                'error': str or None,
                'timestamp': datetime
            }
        """
        print("\n" + "="*60, flush=True)
        print("AUTO CONTENT SYSTEM - Starting Workflow", flush=True)
        print("="*60, flush=True)

        result = {
            'success': False,
            'content_id': None,
            'message_id': None,
            'image_path': None,
            'topic': None,
            'error': None,
            'timestamp': datetime.utcnow()
        }

        try:
            # Step 1: Select unique topic
            print("\n[STEP 1/7] Selecting unique topic...", flush=True)
            topic = self._select_topic()
            if not topic:
                result['error'] = "No suitable topic found"
                print(f"[ERROR] {result['error']}", flush=True)
                return result

            result['topic'] = topic
            print(f"[OK] Selected topic: {topic['keywords'][:3]}", flush=True)

            # Step 2: Get posts for topic
            print("\n[STEP 2/7] Fetching posts for topic...", flush=True)
            posts = self._get_posts_for_topic(topic)
            if not posts:
                result['error'] = f"No posts found for topic: {topic['keywords']}"
                print(f"[ERROR] {result['error']}", flush=True)
                return result

            print(f"[OK] Found {len(posts)} posts", flush=True)

            # Step 3: Generate content
            print("\n[STEP 3/7] Generating content...", flush=True)
            content = self._generate_content(posts)
            if not content:
                result['error'] = "Content generation failed"
                print(f"[ERROR] {result['error']}", flush=True)
                return result

            print(f"[OK] Content generated: {len(content.get('content', ''))} chars", flush=True)

            # Step 4: Save content to database
            print("\n[STEP 4/7] Saving content to database...", flush=True)
            content_id = self._save_content(content, topic)
            if not content_id:
                result['error'] = "Failed to save content to database"
                print(f"[ERROR] {result['error']}", flush=True)
                return result

            result['content_id'] = content_id
            print(f"[OK] Content saved with ID: {content_id}", flush=True)

            # Step 5: Mark topic as used
            print("\n[STEP 5/7] Marking topic as used...", flush=True)
            self.topic_selector.mark_topic_used(topic, content_id)
            print(f"[OK] Topic marked as used", flush=True)

            # Step 6: Generate reel (optional)
            image_path = None
            if self.config['enable_reel']:
                print("\n[STEP 6/7] Generating reel image...", flush=True)
                try:
                    image_path = self.reel_generator.generate_from_content(
                        content,
                        aspect_ratio=self.config['reel_aspect_ratio'],
                        style=self.config['reel_style']
                    )
                    result['image_path'] = image_path
                    print(f"[OK] Reel generated: {image_path}", flush=True)
                except Exception as e:
                    print(f"[WARNING] Reel generation failed: {e}", flush=True)
                    print(f"[WARNING] Continuing without image...", flush=True)
            else:
                print("\n[STEP 6/7] Reel generation disabled", flush=True)

            # Step 7: Post to Telegram (optional)
            if self.config['enable_telegram'] and self.telegram_poster:
                print("\n[STEP 7/7] Posting to Telegram...", flush=True)
                post_result = await self._post_to_telegram(content, image_path)

                if post_result['success']:
                    result['message_id'] = post_result['message_id']
                    print(f"[OK] Posted to Telegram: Message ID {result['message_id']}", flush=True)

                    # Mark as published
                    self.db.mark_content_published(content_id, 'telegram')
                    print(f"[OK] Content marked as published", flush=True)
                else:
                    result['error'] = f"Telegram posting failed: {post_result['error']}"
                    print(f"[WARNING] {result['error']}", flush=True)
                    # Don't fail the whole workflow if posting fails
                    # Content is still saved and can be posted manually
            else:
                print("\n[STEP 7/7] Telegram posting disabled", flush=True)

            # Success!
            result['success'] = True
            print("\n" + "="*60, flush=True)
            print("WORKFLOW COMPLETED SUCCESSFULLY", flush=True)
            print("="*60, flush=True)

            return result

        except Exception as e:
            error_msg = f"Unexpected error in workflow: {str(e)}"
            result['error'] = error_msg
            print(f"\n[ERROR] {error_msg}", flush=True)
            print(f"[ERROR] Traceback:\n{traceback.format_exc()}", flush=True)
            return result

    def _select_topic(self) -> Optional[Dict]:
        """
        Select unique topic using TopicSelector

        Returns:
            Topic dictionary or None if no topic available
        """
        try:
            return self.topic_selector.select_next_topic(
                exclude_days=self.config['topic_exclude_days'],
                prefer_trending=self.config['topic_prefer_trending'],
                min_posts=self.config['topic_min_posts']
            )
        except Exception as e:
            print(f"[ERROR] Topic selection failed: {e}", flush=True)
            return None

    def _get_posts_for_topic(self, topic: Dict) -> List[UniversalPost]:
        """
        Get posts for selected topic from database

        Args:
            topic: Topic dictionary from TopicSelector

        Returns:
            List of UniversalPost objects
        """
        try:
            post_ids = topic.get('posts', [])
            if not post_ids:
                return []

            posts = self.db.session.query(UniversalPost).filter(
                UniversalPost.id.in_(post_ids)
            ).all()

            return posts
        except Exception as e:
            print(f"[ERROR] Failed to get posts: {e}", flush=True)
            return []

    def _generate_content(self, posts: List[UniversalPost]) -> Optional[Dict]:
        """
        Generate content using ContentGenerator

        Args:
            posts: List of posts to analyze

        Returns:
            Generated content dictionary or None
        """
        try:
            return self.content_generator.generate_from_cluster(
                cluster_posts=posts,
                format_type=self.config['content_format'],
                tone=self.config['content_tone'],
                language=self.config['content_language']
            )
        except Exception as e:
            print(f"[ERROR] Content generation failed: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            return None

    def _save_content(self, content: Dict, topic: Dict) -> Optional[int]:
        """
        Save generated content to database

        Args:
            content: Generated content
            topic: Topic that was used

        Returns:
            Content ID or None if save failed
        """
        try:
            # Prepare content data for database
            content_data = {
                'format': self.config['content_format'],
                'language': self.config['content_language'],
                'tone': self.config['content_tone'],
                'title': content.get('title', ''),
                'content': content['content'],
                'hashtags': content.get('hashtags', []),
                'key_points': content.get('key_points', []),
                'word_count': len(str(content['content'])),
                'source_type': 'topic',
                'source_description': f"Topic: {', '.join(topic['keywords'][:3])}",
                'source_posts': topic.get('posts', [])
            }

            return self.db.save_generated_content(content_data)
        except Exception as e:
            print(f"[ERROR] Failed to save content: {e}", flush=True)
            return None

    async def _post_to_telegram(self, content: Dict, image_path: Optional[str] = None) -> Dict:
        """
        Post content to Telegram

        Args:
            content: Generated content
            image_path: Optional path to reel image

        Returns:
            Result dictionary from TelegramPoster
        """
        try:
            # Format content for Telegram
            telegram_content = {
                'format_type': self.config['content_format'],
                'title': content.get('title'),
                'content': content['content'],
                'hashtags': content.get('hashtags', [])
            }

            return await self.telegram_poster.post_content(
                telegram_content,
                media_path=image_path
            )
        except Exception as e:
            print(f"[ERROR] Telegram posting failed: {e}", flush=True)
            return {
                'success': False,
                'message_id': None,
                'error': str(e),
                'posted_at': datetime.utcnow()
            }

    def get_stats(self) -> Dict:
        """
        Get system statistics

        Returns:
            Dictionary with various statistics
        """
        try:
            topic_stats = self.topic_selector.get_usage_stats(days_back=30)
            generated_content = self.db.get_generated_content(limit=100)
            published_content = self.db.get_generated_content(limit=100, only_published=True)

            return {
                'topics_used_30d': topic_stats['total_used'],
                'topics_per_week': topic_stats['topics_per_week'],
                'total_generated': len(generated_content),
                'total_published': len(published_content),
                'publish_rate': len(published_content) / len(generated_content) if generated_content else 0,
                'last_run': topic_stats['most_recent'],
                'config': self.config
            }
        except Exception as e:
            print(f"[ERROR] Failed to get stats: {e}", flush=True)
            return {}

    async def test_components(self) -> Dict:
        """
        Test all components to verify they're working

        Returns:
            Dictionary with test results for each component
        """
        print("\n" + "="*60, flush=True)
        print("TESTING COMPONENTS", flush=True)
        print("="*60, flush=True)

        results = {}

        # Test TopicSelector
        print("\n[TEST] TopicSelector...", flush=True)
        try:
            topic = self.topic_selector.select_next_topic(min_posts=2)
            results['topic_selector'] = {
                'success': topic is not None,
                'message': f"Found topic: {topic['keywords'][:3]}" if topic else "No topics available"
            }
        except Exception as e:
            results['topic_selector'] = {'success': False, 'message': str(e)}

        # Test ContentGenerator
        print("\n[TEST] ContentGenerator...", flush=True)
        try:
            # Get a few posts to test
            posts = self.db.get_recent_posts(limit=5)
            if posts:
                content = self.content_generator.generate_from_cluster(
                    cluster_posts=posts[:3],
                    format_type='long_post',
                    tone='professional',
                    language='ru'
                )
                results['content_generator'] = {
                    'success': content is not None,
                    'message': f"Generated {len(content.get('content', ''))} chars" if content else "Generation failed"
                }
            else:
                results['content_generator'] = {'success': False, 'message': "No posts in database"}
        except Exception as e:
            results['content_generator'] = {'success': False, 'message': str(e)}

        # Test ReelGenerator
        print("\n[TEST] ReelGenerator...", flush=True)
        try:
            test_image = self.reel_generator.generate_reel(
                title='Test',
                key_points=['Point 1', 'Point 2'],
                aspect_ratio='square',
                style='modern'
            )
            results['reel_generator'] = {
                'success': test_image is not None,
                'message': f"Generated: {test_image}"
            }
        except Exception as e:
            results['reel_generator'] = {'success': False, 'message': str(e)}

        # Test TelegramPoster
        if self.telegram_poster:
            print("\n[TEST] TelegramPoster...", flush=True)
            try:
                connected = await self.telegram_poster.test_connection()
                results['telegram_poster'] = {
                    'success': connected,
                    'message': "Connected successfully" if connected else "Connection failed"
                }
            except Exception as e:
                results['telegram_poster'] = {'success': False, 'message': str(e)}
        else:
            results['telegram_poster'] = {'success': False, 'message': "Not configured"}

        # Summary
        print("\n" + "="*60, flush=True)
        print("TEST RESULTS", flush=True)
        print("="*60, flush=True)
        for component, result in results.items():
            status = "[OK]" if result['success'] else "[FAIL]"
            print(f"{status} {component}: {result['message']}", flush=True)

        return results


# Synchronous wrapper for Flask routes
def sync_generate_and_post(auto_system: AutoContentSystem) -> Dict:
    """
    Synchronous wrapper for generate_and_post

    Use this in Flask routes or other synchronous contexts.

    Args:
        auto_system: AutoContentSystem instance

    Returns:
        Result dictionary
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(auto_system.generate_and_post())
        return result
    finally:
        loop.close()
