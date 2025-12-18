"""
Enhanced database manager with deduplication and universal models
"""
from sqlalchemy.orm import Session, sessionmaker
from storage.universal_models import (
    UniversalPost, UniversalComment, DuplicateGroup,
    EnhancedSignal, ParserRun, init_universal_db
)
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
import json
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

    def close(self):
        """Close database session"""
        self.session.close()
