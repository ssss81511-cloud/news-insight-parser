"""
Topic Selector for Automation

Selects unique topics for content generation, ensuring we don't repeat
topics that were recently used.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Tuple
import json
from storage.universal_database import UniversalDatabaseManager
from sqlalchemy import text


class TopicSelector:
    """
    Selects unique topics for automated content generation

    Features:
    - Prevents topic repetition within configurable time window
    - Prefers trending topics when available
    - Tracks topic usage history
    - Supports multiple selection strategies
    """

    def __init__(self, db_manager: UniversalDatabaseManager):
        """
        Initialize TopicSelector

        Args:
            db_manager: Database manager instance for accessing topics and tracking usage
        """
        self.db = db_manager

    def select_next_topic(self, exclude_days: int = 30,
                         prefer_trending: bool = True,
                         min_posts: int = 3) -> Optional[Dict]:
        """
        Select next unique topic for content generation

        Args:
            exclude_days: Don't select topics used within this many days (default: 30)
            prefer_trending: Prioritize trending topics if available (default: True)
            min_posts: Minimum number of posts a topic should have (default: 3)

        Returns:
            Dict with topic info: {
                'topic_id': int,
                'keywords': List[str],
                'post_count': int,
                'is_trending': bool,
                'posts': List[post_ids]
            }
            or None if no suitable topic found
        """
        print(f"[TOPIC SELECTOR] Starting selection (exclude_days={exclude_days}, prefer_trending={prefer_trending})", flush=True)

        # Get available topics from analytics
        available_topics = self._get_available_topics(min_posts=min_posts)

        if not available_topics:
            print(f"[TOPIC SELECTOR] No topics found with min_posts={min_posts}", flush=True)
            return None

        print(f"[TOPIC SELECTOR] Found {len(available_topics)} candidate topics", flush=True)

        # Filter out recently used topics
        unused_topics = []
        for topic in available_topics:
            keywords = topic['keywords']
            if not self.db.is_topic_used_recently(keywords, exclude_days):
                unused_topics.append(topic)
            else:
                print(f"[TOPIC SELECTOR] Skipping recently used topic: {keywords[:3]}", flush=True)

        if not unused_topics:
            print(f"[TOPIC SELECTOR] All topics were used recently. Relaxing constraint...", flush=True)
            # All topics were used recently - relax the constraint
            if exclude_days > 7:
                return self.select_next_topic(exclude_days=exclude_days // 2,
                                            prefer_trending=prefer_trending,
                                            min_posts=min_posts)
            else:
                # Even with relaxed constraints, no topics - just use the first available
                print(f"[TOPIC SELECTOR] Using first available topic despite recent use", flush=True)
                return available_topics[0] if available_topics else None

        print(f"[TOPIC SELECTOR] {len(unused_topics)} unused topics available", flush=True)

        # Select topic based on preferences
        if prefer_trending:
            # Try to find trending topics first
            trending_topics = [t for t in unused_topics if t.get('is_trending', False)]
            if trending_topics:
                selected = trending_topics[0]
                print(f"[TOPIC SELECTOR] Selected trending topic: {selected['keywords'][:3]}", flush=True)
                return selected

        # Return topic with most posts (highest quality signal)
        selected = max(unused_topics, key=lambda t: t['post_count'])
        print(f"[TOPIC SELECTOR] Selected topic with {selected['post_count']} posts: {selected['keywords'][:3]}", flush=True)
        return selected

    def _get_available_topics(self, min_posts: int = 3) -> List[Dict]:
        """
        Get available topics from database

        This queries the analytics results to find topics with sufficient posts.

        Args:
            min_posts: Minimum number of posts required

        Returns:
            List of topic dictionaries
        """
        topics = []

        try:
            # Query the database for topic analysis results
            # Topics are stored in the 'topics' table from analytics
            query = text("""
                SELECT
                    topic_id,
                    keywords,
                    post_count,
                    avg_importance,
                    created_at
                FROM topics
                WHERE post_count >= :min_posts
                ORDER BY post_count DESC, avg_importance DESC
                LIMIT 50
            """)

            result = self.db.session.execute(query, {'min_posts': min_posts})
            rows = result.fetchall()

            for row in rows:
                topic_id, keywords_json, post_count, avg_importance, created_at = row

                # Parse keywords
                try:
                    keywords = json.loads(keywords_json) if isinstance(keywords_json, str) else keywords_json
                except:
                    keywords = keywords_json.split(',') if isinstance(keywords_json, str) else []

                # Get posts for this topic
                post_ids = self._get_posts_for_topic(keywords)

                # Determine if trending (created recently with high importance)
                is_trending = False
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                    is_trending = age_hours < 72 and avg_importance > 50  # Last 3 days, high importance

                topics.append({
                    'topic_id': topic_id,
                    'keywords': keywords,
                    'post_count': post_count,
                    'avg_importance': avg_importance,
                    'is_trending': is_trending,
                    'posts': post_ids
                })

        except Exception as e:
            print(f"[TOPIC SELECTOR] Error querying topics table: {e}", flush=True)
            # Fallback: Generate ad-hoc topics from recent high-importance posts
            topics = self._generate_adhoc_topics(min_posts)

        return topics

    def _get_posts_for_topic(self, keywords: List[str], lookback_days: int = 7) -> List[int]:
        """
        Get post IDs that match the topic keywords

        Args:
            keywords: List of keywords defining the topic
            lookback_days: How many days to look back

        Returns:
            List of post IDs
        """
        try:
            from storage.universal_models import UniversalPost
            from datetime import datetime, timedelta, timezone

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            # Find posts that contain any of the keywords
            posts = []
            for keyword in keywords[:5]:  # Limit to first 5 keywords
                keyword_posts = self.db.session.query(UniversalPost.id).filter(
                    UniversalPost.created_at >= cutoff_date,
                    (UniversalPost.title.ilike(f'%{keyword}%')) |
                    (UniversalPost.content.ilike(f'%{keyword}%'))
                ).limit(20).all()

                posts.extend([p.id for p in keyword_posts])

            # Remove duplicates and return
            return list(set(posts))[:15]  # Max 15 posts per topic

        except Exception as e:
            print(f"[TOPIC SELECTOR] Error getting posts for topic: {e}", flush=True)
            return []

    def _generate_adhoc_topics(self, min_posts: int = 3) -> List[Dict]:
        """
        Generate ad-hoc topics from recent posts when topics table is not available

        This is a fallback method that groups posts by common keywords.

        Args:
            min_posts: Minimum posts required

        Returns:
            List of ad-hoc topics
        """
        print(f"[TOPIC SELECTOR] Generating ad-hoc topics from recent posts", flush=True)

        try:
            from storage.universal_models import UniversalPost
            from collections import Counter
            from datetime import datetime, timedelta, timezone

            # Get recent high-importance posts with AI analysis
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            posts = self.db.session.query(UniversalPost).filter(
                UniversalPost.created_at >= cutoff_date,
                UniversalPost.importance_score >= 50,
                UniversalPost.ai_summary != None
            ).order_by(UniversalPost.importance_score.desc()).limit(100).all()

            if not posts:
                print(f"[TOPIC SELECTOR] No posts with AI analysis found", flush=True)
                return []

            # Extract topics from AI analysis
            all_topics = []
            for post in posts:
                if post.ai_topics:
                    try:
                        topics = json.loads(post.ai_topics)
                        all_topics.extend(topics)
                    except:
                        pass

            # Count topic frequency
            topic_counts = Counter(all_topics)

            # Create topics from most common
            adhoc_topics = []
            for topic, count in topic_counts.most_common(10):
                if count >= min_posts:
                    keywords = [topic]  # Simple single-keyword topic
                    post_ids = self._get_posts_for_topic(keywords)

                    if len(post_ids) >= min_posts:
                        adhoc_topics.append({
                            'topic_id': None,
                            'keywords': keywords,
                            'post_count': len(post_ids),
                            'avg_importance': 60.0,  # Estimated
                            'is_trending': True,  # Recent posts
                            'posts': post_ids
                        })

            print(f"[TOPIC SELECTOR] Generated {len(adhoc_topics)} ad-hoc topics", flush=True)
            return adhoc_topics

        except Exception as e:
            print(f"[TOPIC SELECTOR] Error generating ad-hoc topics: {e}", flush=True)
            return []

    def mark_topic_used(self, topic: Dict, content_id: int) -> bool:
        """
        Mark a topic as used after content generation

        Args:
            topic: Topic dictionary from select_next_topic()
            content_id: ID of generated content

        Returns:
            True if successfully marked, False otherwise
        """
        try:
            used_id = self.db.mark_topic_as_used(
                keywords=topic['keywords'],
                content_id=content_id,
                topic_id=topic.get('topic_id'),
                post_count=topic.get('post_count', 0),
                source_type='topic'
            )

            success = used_id > 0
            if success:
                print(f"[TOPIC SELECTOR] Marked topic as used: {topic['keywords'][:3]}", flush=True)
            return success

        except Exception as e:
            print(f"[TOPIC SELECTOR] Error marking topic as used: {e}", flush=True)
            return False

    def get_usage_stats(self, days_back: int = 30) -> Dict:
        """
        Get statistics about topic usage

        Args:
            days_back: How many days to look back

        Returns:
            Dictionary with usage statistics
        """
        try:
            used_topics = self.db.get_used_topics(days_back=days_back)

            return {
                'total_used': len(used_topics),
                'days_analyzed': days_back,
                'topics_per_week': len(used_topics) / (days_back / 7) if days_back > 0 else 0,
                'most_recent': used_topics[0].used_at if used_topics else None
            }

        except Exception as e:
            print(f"[TOPIC SELECTOR] Error getting usage stats: {e}", flush=True)
            return {
                'total_used': 0,
                'days_analyzed': days_back,
                'topics_per_week': 0,
                'most_recent': None
            }
