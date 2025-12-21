"""
Enhanced database manager with deduplication and universal models
"""
from sqlalchemy.orm import Session, sessionmaker
from storage.universal_models import (
    UniversalPost, UniversalComment, DuplicateGroup,
    EnhancedSignal, ParserRun, UsedTopic, init_universal_db
)
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
import json
import hashlib
from difflib import SequenceMatcher


class UniversalDatabaseManager:
    """
    Enhanced database manager with:
    - Deduplication between sources
    - Signal prioritization
    - Context preservation
    """

    def __init__(self, database_url='sqlite:///data/insights.db'):
        self.engine = init_universal_db(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def reset_session(self):
        """Reset the database session - useful after errors"""
        try:
            self.session.close()
        except:
            pass
        self.session = self.Session()

    def add_universal_post(self, post_data: dict) -> UniversalPost:
        """
        Add or update universal post with deduplication

        Args:
            post_data: Normalized post data

        Returns:
            UniversalPost instance
        """
        try:
            # Check if post already exists from this source
            existing = self.session.query(UniversalPost).filter_by(
                source=post_data['source'],
                source_id=post_data['source_id']
            ).first()

            if existing:
                # Update existing post (score may have changed)
                for key, value in post_data.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
                post = existing
            else:
                # Create new post
                post = UniversalPost(**post_data)
                self.session.add(post)
                self.session.flush()  # Get ID before checking duplicates

                # Check for duplicates from other sources
                self._check_and_link_duplicates(post)

            self.session.commit()
            return post
        except Exception as e:
            self.session.rollback()
            raise e

    def _check_and_link_duplicates(self, new_post: UniversalPost):
        """
        Check if this post is duplicate of existing posts from other sources

        Uses:
        - Content hash similarity
        - Title similarity
        - Time proximity (posted around same time)
        """
        # Find posts with similar content hash or title
        similar_posts = self.session.query(UniversalPost).filter(
            UniversalPost.id != new_post.id,
            UniversalPost.source != new_post.source,  # Different source
        ).filter(
            (UniversalPost.content_hash == new_post.content_hash) |  # Same hash
            (UniversalPost.title.like(f'%{new_post.title[:50]}%'))  # Similar title
        ).all()

        for similar_post in similar_posts:
            # Calculate similarity
            similarity = self._calculate_similarity(new_post, similar_post)

            if similarity > 0.7:  # 70% similar
                # They are duplicates - link them
                if similar_post.duplicate_group_id:
                    # Add to existing group
                    new_post.duplicate_group_id = similar_post.duplicate_group_id
                else:
                    # Create new duplicate group
                    group = DuplicateGroup(
                        canonical_title=new_post.title,
                        similarity_score=similarity
                    )
                    self.session.add(group)
                    self.session.flush()

                    similar_post.duplicate_group_id = group.id
                    new_post.duplicate_group_id = group.id

                self.session.commit()
                break

    def _calculate_similarity(self, post1: UniversalPost, post2: UniversalPost) -> float:
        """
        Calculate similarity between two posts

        Returns:
            Similarity score 0-1
        """
        # Title similarity
        title_sim = SequenceMatcher(None, post1.title.lower(), post2.title.lower()).ratio()

        # Content similarity (if both have content)
        content_sim = 0.0
        if post1.content and post2.content:
            content_sim = SequenceMatcher(None, post1.content[:500].lower(), post2.content[:500].lower()).ratio()

        # Time proximity (posted within 24 hours)
        time_diff = abs((post1.created_at - post2.created_at).total_seconds())
        time_sim = max(0, 1 - (time_diff / 86400))  # 1.0 if same time, 0 if >24h apart

        # Weighted average
        similarity = (title_sim * 0.5) + (content_sim * 0.3) + (time_sim * 0.2)

        return similarity

    def add_universal_comment(self, comment_data: dict) -> UniversalComment:
        """Add or update universal comment"""
        try:
            existing = self.session.query(UniversalComment).filter_by(
                source=comment_data['source'],
                source_id=comment_data['source_id']
            ).first()

            if existing:
                for key, value in comment_data.items():
                    setattr(existing, key, value)
                comment = existing
            else:
                comment = UniversalComment(**comment_data)
                self.session.add(comment)

            self.session.commit()
            return comment
        except Exception as e:
            self.session.rollback()
            raise e

    def add_enhanced_signal(self, signal_data: dict) -> EnhancedSignal:
        """
        Add enhanced signal with prioritization and context

        Args:
            signal_data: Signal data including priority, context, etc.
        """
        try:
            signal = EnhancedSignal(**signal_data)

            # Calculate importance score based on multiple factors
            signal.importance_score = self._calculate_signal_importance(signal)

            # Determine priority level
            signal.priority = self._determine_priority(signal.importance_score, signal.frequency)

            # Check if trending
            signal.is_trending = self._check_if_trending(signal)

            self.session.add(signal)
            self.session.commit()
            return signal
        except Exception as e:
            self.session.rollback()
            raise e

    def _calculate_signal_importance(self, signal: EnhancedSignal) -> float:
        """
        Calculate importance score for a signal (0-100)

        Factors:
        - Frequency of mentions
        - Growth rate
        - Cross-source presence
        - Confidence score
        """
        score = 0.0

        # Frequency (40 points)
        score += min(signal.frequency * 2, 40)

        # Growth rate (30 points)
        if signal.growth_rate > 0:
            score += min(signal.growth_rate * 10, 30)

        # Cross-source bonus (20 points)
        if signal.is_cross_source:
            sources = json.loads(signal.sources) if signal.sources else []
            score += min(len(sources) * 10, 20)

        # Confidence (10 points)
        score += signal.confidence_score * 0.1

        return min(score, 100)

    def _determine_priority(self, importance_score: float, frequency: int) -> str:
        """Determine priority level based on importance and frequency"""
        if importance_score >= 80 and frequency >= 10:
            return 'critical'
        elif importance_score >= 60 and frequency >= 5:
            return 'high'
        elif importance_score >= 40:
            return 'medium'
        else:
            return 'low'

    def _check_if_trending(self, signal: EnhancedSignal) -> bool:
        """Check if signal is currently trending"""
        # Trending if:
        # - High growth rate
        # - Seen recently
        # - High velocity
        if signal.growth_rate > 0.5 and signal.velocity > 1.0:
            time_since_last = (datetime.now(timezone.utc) - signal.last_seen).total_seconds() / 3600
            return time_since_last < 48  # Seen in last 48 hours
        return False

    def find_duplicate_posts(self, post: UniversalPost) -> List[UniversalPost]:
        """Find all duplicate posts across sources"""
        if not post.duplicate_group_id:
            return []

        return self.session.query(UniversalPost).filter(
            UniversalPost.duplicate_group_id == post.duplicate_group_id,
            UniversalPost.id != post.id
        ).all()

    def get_post_by_id(self, post_id: int) -> Optional[UniversalPost]:
        """Get a single post by ID"""
        try:
            return self.session.query(UniversalPost).filter_by(id=post_id).first()
        except Exception as e:
            self.reset_session()
            return self.session.query(UniversalPost).filter_by(id=post_id).first()

    def get_post_comments(self, post_id: int) -> List[UniversalComment]:
        """Get all comments for a post"""
        try:
            return self.session.query(UniversalComment).filter_by(
                post_id=post_id
            ).order_by(UniversalComment.created_at.desc()).all()
        except Exception as e:
            self.reset_session()
            return self.session.query(UniversalComment).filter_by(
                post_id=post_id
            ).order_by(UniversalComment.created_at.desc()).all()

    def save_ai_analysis(self, post_id: int, analysis: dict):
        """
        Save AI analysis results to post

        Args:
            post_id: Post ID
            analysis: Dict with AI analysis results
        """
        try:
            post = self.session.query(UniversalPost).filter_by(id=post_id).first()
            if post:
                import json
                post.ai_summary = analysis.get('summary', '')
                post.ai_category = analysis.get('category', '')
                post.ai_sentiment = analysis.get('sentiment', '')
                post.ai_insights = json.dumps(analysis.get('key_insights', []))
                post.ai_technologies = json.dumps(analysis.get('technologies', []))
                post.ai_companies = json.dumps(analysis.get('companies', []))
                post.ai_topics = json.dumps(analysis.get('topics', []))
                post.ai_analyzed_at = datetime.now(timezone.utc)
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"Error saving AI analysis: {e}")

    def get_recent_posts(self, limit: int = 50, post_type: Optional[str] = None,
                        source: Optional[str] = None, min_importance: float = 0.0,
                        search_query: Optional[str] = None) -> List[UniversalPost]:
        """Get recent posts with filtering and search"""
        try:
            query = self.session.query(UniversalPost).filter(
                UniversalPost.importance_score >= min_importance
            )

            if post_type:
                query = query.filter_by(post_type=post_type)
            if source:
                query = query.filter_by(source=source)

            # Full-text search
            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(
                    (UniversalPost.title.ilike(search_pattern)) |
                    (UniversalPost.content.ilike(search_pattern))
                )

            return query.order_by(UniversalPost.fetched_at.desc()).limit(limit).all()
        except Exception as e:
            # Reset session and try again
            self.reset_session()
            query = self.session.query(UniversalPost).filter(
                UniversalPost.importance_score >= min_importance
            )

            if post_type:
                query = query.filter_by(post_type=post_type)
            if source:
                query = query.filter_by(source=source)

            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(
                    (UniversalPost.title.ilike(search_pattern)) |
                    (UniversalPost.content.ilike(search_pattern))
                )

            return query.order_by(UniversalPost.fetched_at.desc()).limit(limit).all()

    def get_prioritized_signals(self, limit: int = 20, priority: Optional[str] = None,
                               only_trending: bool = False) -> List[EnhancedSignal]:
        """Get signals with prioritization"""
        try:
            query = self.session.query(EnhancedSignal).filter_by(is_active=True)

            if priority:
                query = query.filter_by(priority=priority)
            if only_trending:
                query = query.filter_by(is_trending=True)

            return query.order_by(
                EnhancedSignal.importance_score.desc(),
                EnhancedSignal.last_seen.desc()
            ).limit(limit).all()
        except Exception as e:
            # Reset session and try again
            self.reset_session()
            query = self.session.query(EnhancedSignal).filter_by(is_active=True)

            if priority:
                query = query.filter_by(priority=priority)
            if only_trending:
                query = query.filter_by(is_trending=True)

            return query.order_by(
                EnhancedSignal.importance_score.desc(),
                EnhancedSignal.last_seen.desc()
            ).limit(limit).all()

    def get_cross_source_signals(self) -> List[EnhancedSignal]:
        """Get signals that appear across multiple sources"""
        try:
            return self.session.query(EnhancedSignal).filter_by(
                is_cross_source=True,
                is_active=True
            ).order_by(EnhancedSignal.importance_score.desc()).all()
        except Exception as e:
            # Reset session and try again
            self.reset_session()
            return self.session.query(EnhancedSignal).filter_by(
                is_cross_source=True,
                is_active=True
            ).order_by(EnhancedSignal.importance_score.desc()).all()

    def get_stats(self) -> dict:
        """Get overall statistics"""
        try:
            return {
                'total_posts': self.session.query(UniversalPost).count(),
                'total_comments': self.session.query(UniversalComment).count(),
                'total_signals': self.session.query(EnhancedSignal).filter_by(is_active=True).count(),
                'critical_signals': self.session.query(EnhancedSignal).filter_by(
                    priority='critical', is_active=True
                ).count(),
                'trending_signals': self.session.query(EnhancedSignal).filter_by(
                    is_trending=True, is_active=True
                ).count(),
                'duplicate_groups': self.session.query(DuplicateGroup).count(),

                # By source
                'hacker_news_posts': self.session.query(UniversalPost).filter_by(source='hacker_news').count(),
                'reddit_posts': self.session.query(UniversalPost).filter_by(source='reddit').count(),
                'product_hunt_posts': self.session.query(UniversalPost).filter_by(source='product_hunt').count(),

                # By type
                'ask_posts': self.session.query(UniversalPost).filter_by(post_type='ask_hn').count(),
                'show_posts': self.session.query(UniversalPost).filter_by(post_type='show_hn').count(),
                'new_posts': self.session.query(UniversalPost).filter_by(post_type='new').count(),
            }
        except Exception as e:
            # If there's a session error, reset it and try again
            self.reset_session()
            return {
                'total_posts': self.session.query(UniversalPost).count(),
                'total_comments': self.session.query(UniversalComment).count(),
                'total_signals': self.session.query(EnhancedSignal).filter_by(is_active=True).count(),
                'critical_signals': self.session.query(EnhancedSignal).filter_by(
                    priority='critical', is_active=True
                ).count(),
                'trending_signals': self.session.query(EnhancedSignal).filter_by(
                    is_trending=True, is_active=True
                ).count(),
                'duplicate_groups': self.session.query(DuplicateGroup).count(),

                # By source
                'hacker_news_posts': self.session.query(UniversalPost).filter_by(source='hacker_news').count(),
                'reddit_posts': self.session.query(UniversalPost).filter_by(source='reddit').count(),
                'product_hunt_posts': self.session.query(UniversalPost).filter_by(source='product_hunt').count(),

                # By type
                'ask_posts': self.session.query(UniversalPost).filter_by(post_type='ask_hn').count(),
                'show_posts': self.session.query(UniversalPost).filter_by(post_type='show_hn').count(),
                'new_posts': self.session.query(UniversalPost).filter_by(post_type='new').count(),
            }

    def start_parser_run(self, source: str, section: str) -> ParserRun:
        """Start tracking parser run"""
        try:
            run = ParserRun(
                source=source,
                section=section,
                status='running',
                started_at=datetime.now(timezone.utc)
            )
            self.session.add(run)
            self.session.commit()
            return run
        except Exception as e:
            self.session.rollback()
            raise e

    def finish_parser_run(self, run_id: int, items_fetched: int,
                         status: str = 'success', error: str = None):
        """Finish tracking parser run"""
        try:
            run = self.session.query(ParserRun).filter_by(id=run_id).first()
            if run:
                run.items_fetched = items_fetched
                run.finished_at = datetime.now(timezone.utc)
                run.status = status
                run.error_message = error
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def get_parser_runs(self, limit: int = 10) -> List[ParserRun]:
        """Get recent parser runs"""
        try:
            return self.session.query(ParserRun).order_by(
                ParserRun.started_at.desc()
            ).limit(limit).all()
        except Exception as e:
            # Reset session and try again
            self.reset_session()
            return self.session.query(ParserRun).order_by(
                ParserRun.started_at.desc()
            ).limit(limit).all()

    def cleanup_old_posts(self, days_old: int = 60) -> int:
        """
        Delete posts older than specified days

        Args:
            days_old: Delete posts older than this many days (default: 60 = 2 months)

        Returns:
            Number of posts deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            # Delete old posts
            deleted_count = self.session.query(UniversalPost).filter(
                UniversalPost.created_at < cutoff_date
            ).delete()

            # Delete old comments
            self.session.query(UniversalComment).filter(
                UniversalComment.created_at < cutoff_date
            ).delete()

            self.session.commit()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            print(f"Error cleaning up old posts: {e}")
            return 0

    def save_generated_content(self, content_data: dict) -> int:
        """
        Save AI-generated content to database

        Args:
            content_data: Dict with content data

        Returns:
            ID of saved content
        """
        try:
            from storage.universal_models import GeneratedContent

            content = GeneratedContent(
                format_type=content_data['format'],
                language=content_data.get('language', 'en'),
                tone=content_data.get('tone', 'professional'),
                title=content_data.get('title', ''),
                content=json.dumps(content_data['content']) if isinstance(content_data['content'], list) else content_data['content'],
                hashtags=json.dumps(content_data.get('hashtags', [])),
                key_points=json.dumps(content_data.get('key_points', [])),
                word_count=content_data.get('word_count', 0),
                source_type=content_data.get('source_type', 'unknown'),
                source_description=content_data.get('source_description', ''),
                source_posts=json.dumps(content_data.get('source_posts', []))
            )

            self.session.add(content)
            self.session.commit()
            return content.id
        except Exception as e:
            self.session.rollback()
            print(f"Error saving generated content: {e}")
            return 0

    def get_generated_content(self, limit: int = 50, format_type: Optional[str] = None,
                              only_published: bool = False) -> List:
        """Get generated content with filtering"""
        try:
            from storage.universal_models import GeneratedContent

            query = self.session.query(GeneratedContent)

            if format_type:
                query = query.filter_by(format_type=format_type)
            if only_published:
                query = query.filter_by(is_published=True)

            return query.order_by(GeneratedContent.created_at.desc()).limit(limit).all()
        except Exception as e:
            self.reset_session()
            from storage.universal_models import GeneratedContent

            query = self.session.query(GeneratedContent)

            if format_type:
                query = query.filter_by(format_type=format_type)
            if only_published:
                query = query.filter_by(is_published=True)

            return query.order_by(GeneratedContent.created_at.desc()).limit(limit).all()

    def get_content_by_id(self, content_id: int):
        """Get generated content by ID"""
        try:
            from storage.universal_models import GeneratedContent
            return self.session.query(GeneratedContent).filter_by(id=content_id).first()
        except Exception as e:
            self.reset_session()
            from storage.universal_models import GeneratedContent
            return self.session.query(GeneratedContent).filter_by(id=content_id).first()

    def mark_content_published(self, content_id: int, platform: str):
        """Mark content as published"""
        try:
            from storage.universal_models import GeneratedContent

            content = self.session.query(GeneratedContent).filter_by(id=content_id).first()
            if content:
                content.is_published = True
                content.published_at = datetime.now(timezone.utc)
                content.platform = platform
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"Error marking content as published: {e}")

    def delete_generated_content(self, content_id: int) -> bool:
        """Delete generated content"""
        try:
            from storage.universal_models import GeneratedContent

            content = self.session.query(GeneratedContent).filter_by(id=content_id).first()
            if content:
                self.session.delete(content)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"Error deleting content: {e}")
            return False

    # UsedTopic management methods
    def mark_topic_as_used(self, keywords: List[str], content_id: int = None,
                          topic_id: int = None, post_count: int = 0,
                          source_type: str = 'topic') -> int:
        """
        Mark a topic as used for content generation

        Args:
            keywords: List of keywords defining the topic
            content_id: ID of generated content (if any)
            topic_id: Topic ID from analytics (if applicable)
            post_count: Number of posts in this topic
            source_type: Type of source ('topic', 'trend', 'cluster')

        Returns:
            ID of UsedTopic record
        """
        try:
            # Create hash of keywords for duplicate detection
            keywords_sorted = sorted([k.lower().strip() for k in keywords])
            keywords_str = '|||'.join(keywords_sorted)
            keywords_hash = hashlib.sha256(keywords_str.encode()).hexdigest()

            used_topic = UsedTopic(
                topic_id=topic_id,
                keywords=json.dumps(keywords),
                keywords_hash=keywords_hash,
                content_id=content_id,
                post_count=post_count,
                source_type=source_type,
                used_at=datetime.now(timezone.utc)
            )

            self.session.add(used_topic)
            self.session.commit()
            return used_topic.id
        except Exception as e:
            self.session.rollback()
            print(f"Error marking topic as used: {e}")
            return 0

    def _are_topics_similar(self, keywords1: List[str], keywords2: List[str], threshold: float = 0.5) -> bool:
        """
        Check if two topics are similar based on keyword overlap

        Uses Jaccard similarity: intersection / union

        Args:
            keywords1: First topic keywords
            keywords2: Second topic keywords
            threshold: Similarity threshold (0.0 to 1.0, default 0.5)

        Returns:
            True if topics are similar (above threshold)
        """
        # Normalize keywords
        set1 = set(k.lower().strip() for k in keywords1)
        set2 = set(k.lower().strip() for k in keywords2)

        if not set1 or not set2:
            return False

        # Jaccard similarity = intersection / union
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        similarity = intersection / union if union > 0 else 0.0

        return similarity >= threshold

    def is_topic_used_recently(self, keywords: List[str], exclude_days: int = 30, similarity_threshold: float = 0.5) -> bool:
        """
        Check if topic (or similar topic) was used recently

        Args:
            keywords: List of keywords defining the topic
            exclude_days: Number of days to look back (default: 30)
            similarity_threshold: How similar keywords need to be (0.5 = 50% overlap)

        Returns:
            True if topic or similar topic was used within exclude_days
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=exclude_days)

            # Get all recently used topics
            recent_topics = self.session.query(UsedTopic).filter(
                UsedTopic.used_at >= cutoff_date
            ).all()

            # Check if any recent topic is similar
            for used_topic in recent_topics:
                try:
                    # Parse keywords from used topic
                    used_keywords = json.loads(used_topic.keywords) if isinstance(used_topic.keywords, str) else used_topic.keywords

                    # Check similarity
                    if self._are_topics_similar(keywords, used_keywords, similarity_threshold):
                        # Calculate actual similarity for logging
                        set1 = set(k.lower().strip() for k in keywords)
                        set2 = set(k.lower().strip() for k in used_keywords)
                        intersection = len(set1 & set2)
                        union = len(set1 | set2)
                        similarity = intersection / union if union > 0 else 0.0

                        print(f"[TOPIC FILTER] Similar topic found! New: {keywords[:3]}, Used: {used_keywords[:3]}, Similarity: {similarity:.2f}", flush=True)
                        return True
                except:
                    # If can't parse keywords, skip this topic
                    continue

            return False
        except Exception as e:
            self.reset_session()
            return False

    def get_used_topics(self, days_back: int = 30, limit: int = 50) -> List[UsedTopic]:
        """
        Get list of recently used topics

        Args:
            days_back: How many days to look back
            limit: Maximum number to return

        Returns:
            List of UsedTopic records
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

            return self.session.query(UsedTopic).filter(
                UsedTopic.used_at >= cutoff_date
            ).order_by(UsedTopic.used_at.desc()).limit(limit).all()
        except Exception as e:
            self.reset_session()
            return []

    def cleanup_old_used_topics(self, days_old: int = 90) -> int:
        """
        Delete old used topic records

        Args:
            days_old: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            deleted_count = self.session.query(UsedTopic).filter(
                UsedTopic.used_at < cutoff_date
            ).delete()

            self.session.commit()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            print(f"Error cleaning up old used topics: {e}")
            return 0

    def close(self):
        """Close database session"""
        self.session.close()
