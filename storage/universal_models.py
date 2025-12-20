"""
Universal data models for all sources

These models replace source-specific models (HNPost, RedditPost, etc.)
All data from any source is normalized into these models.
"""
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UniversalPost(Base):
    """
    Universal post model - works for any source

    Maps to:
    - HN: story/question
    - Reddit: submission
    - Product Hunt: post/launch
    - Indie Hackers: post
    """
    __tablename__ = 'universal_posts'

    id = Column(Integer, primary_key=True)

    # Source identification
    source = Column(String(50), index=True)  # 'hacker_news', 'reddit', 'product_hunt'
    source_id = Column(String(100), index=True)  # ID in source system
    source_url = Column(String(1000))  # URL to original post

    # Unified content fields
    title = Column(String(500), index=True)
    content = Column(Text, nullable=True)  # text, selftext, description
    author = Column(String(100), index=True)

    # Engagement metrics (normalized)
    score = Column(Integer, default=0, index=True)  # upvotes, points, votes
    comments_count = Column(Integer, default=0)

    # Classification
    post_type = Column(String(50), index=True)  # 'ask', 'show', 'launch', 'discussion'
    category = Column(String(50), nullable=True)  # topic/category if available

    # Temporal data
    created_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Deduplication
    content_hash = Column(String(64), index=True)  # SHA-256 hash for deduplication

    # Importance scoring
    importance_score = Column(Float, default=0.0, index=True)  # 0-100

    # AI Analysis results
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    ai_category = Column(String(50), nullable=True)  # problem/solution/product/question/discussion
    ai_sentiment = Column(String(20), nullable=True)  # positive/negative/neutral
    ai_insights = Column(Text, nullable=True)  # JSON array of insights
    ai_technologies = Column(Text, nullable=True)  # JSON array of technologies
    ai_companies = Column(Text, nullable=True)  # JSON array of companies
    ai_topics = Column(Text, nullable=True)  # JSON array of topics
    ai_analyzed_at = Column(DateTime, nullable=True)  # When AI analysis was done

    # Relationships
    comments = relationship("UniversalComment", back_populates="post", cascade="all, delete-orphan")
    duplicate_group_id = Column(Integer, ForeignKey('duplicate_groups.id'), nullable=True)
    duplicate_group = relationship("DuplicateGroup", back_populates="posts")

    # Indexes for performance
    __table_args__ = (
        Index('idx_source_source_id', 'source', 'source_id'),
        Index('idx_post_type_score', 'post_type', 'score'),
        Index('idx_created_fetched', 'created_at', 'fetched_at'),
    )

    def __repr__(self):
        return f"<UniversalPost {self.source}:{self.source_id} - {self.title[:50]}>"


class UniversalComment(Base):
    """
    Universal comment model - works for any source

    Maps to:
    - HN: comment
    - Reddit: comment
    - Product Hunt: comment
    """
    __tablename__ = 'universal_comments'

    id = Column(Integer, primary_key=True)

    # Source identification
    source = Column(String(50), index=True)
    source_id = Column(String(100), index=True)

    # Relationship to post
    post_id = Column(Integer, ForeignKey('universal_posts.id'), index=True)
    parent_id = Column(Integer, nullable=True)  # Parent comment ID (for threading)

    # Content
    author = Column(String(100))
    content = Column(Text)

    # Engagement
    score = Column(Integer, default=0)  # upvotes if available

    # Temporal
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=func.now)

    # Relationships
    post = relationship("UniversalPost", back_populates="comments")

    def __repr__(self):
        return f"<UniversalComment {self.source}:{self.source_id}>"


class DuplicateGroup(Base):
    """
    Groups duplicate/similar posts from different sources

    Example:
    - Same product launched on HN, Reddit, and Product Hunt
    - Should be treated as 1 entity, not 3 separate posts
    """
    __tablename__ = 'duplicate_groups'

    id = Column(Integer, primary_key=True)
    canonical_title = Column(String(500))  # Main title to use
    similarity_score = Column(Float)  # How similar the posts are (0-1)
    created_at = Column(DateTime, default=func.now)

    # Relationships
    posts = relationship("UniversalPost", back_populates="duplicate_group")

    def __repr__(self):
        return f"<DuplicateGroup {self.id}: {self.canonical_title[:50]} ({len(self.posts)} posts)>"


class EnhancedSignal(Base):
    """
    Enhanced signal with prioritization and context

    Improvements over basic Signal:
    - Priority scoring
    - Context preservation
    - Source tracking
    - Trend analysis
    """
    __tablename__ = 'enhanced_signals'

    id = Column(Integer, primary_key=True)

    # Signal classification
    signal_type = Column(String(50), index=True)  # 'pain', 'language', 'solution', 'behavior'
    title = Column(String(500))
    description = Column(Text)

    # Priority and importance
    priority = Column(String(20), default='medium', index=True)  # 'critical', 'high', 'medium', 'low'
    importance_score = Column(Float, default=50.0, index=True)  # 0-100
    confidence_score = Column(Float, default=50.0)  # How confident we are (0-100)

    # Frequency and trend
    frequency = Column(Integer, default=1)  # How many mentions
    growth_rate = Column(Float, default=0.0)  # Trend: positive = growing, negative = declining
    velocity = Column(Float, default=0.0)  # How fast it's growing

    # Sources
    sources = Column(Text)  # JSON list: ['hacker_news', 'reddit']
    keywords = Column(Text)  # JSON list of related keywords

    # Context preservation
    context_snippets = Column(Text)  # JSON list of example quotes with context
    example_urls = Column(Text)  # JSON list of URLs

    # Cross-source correlation
    related_signal_ids = Column(Text)  # JSON list of related signal IDs
    is_cross_source = Column(Boolean, default=False)  # True if appears in multiple sources

    # Temporal tracking
    first_seen = Column(DateTime, default=func.now(), index=True)
    last_seen = Column(DateTime, default=func.now(), index=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_trending = Column(Boolean, default=False, index=True)  # Currently trending

    # Indexes
    __table_args__ = (
        Index('idx_priority_importance', 'priority', 'importance_score'),
        Index('idx_type_active', 'signal_type', 'is_active'),
        Index('idx_trending_active', 'is_trending', 'is_active'),
    )

    def __repr__(self):
        return f"<EnhancedSignal {self.signal_type}:{self.priority} - {self.title[:50]}>"


class ParserRun(Base):
    """Track parser execution history"""
    __tablename__ = 'parser_runs'

    id = Column(Integer, primary_key=True)
    source = Column(String(50), index=True)
    section = Column(String(50))
    items_fetched = Column(Integer, default=0)
    started_at = Column(DateTime, default=func.now, index=True)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), index=True)  # 'running', 'success', 'failed'
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ParserRun {self.source}/{self.section} at {self.started_at}>"


class GeneratedContent(Base):
    """
    Store AI-generated social media content

    Tracks all generated posts for reuse and analytics
    """
    __tablename__ = 'generated_content'

    id = Column(Integer, primary_key=True)

    # Content metadata
    format_type = Column(String(20), index=True)  # 'long_post', 'reel', 'thread'
    language = Column(String(10), default='en')  # 'en', 'ru'
    tone = Column(String(20), default='professional')  # 'professional', 'casual', 'inspirational'

    # Generated content
    title = Column(String(200), nullable=True)
    content = Column(Text)  # Full content (or JSON array for threads)
    hashtags = Column(Text)  # JSON array of hashtags
    key_points = Column(Text, nullable=True)  # JSON array of key points

    # Metadata
    word_count = Column(Integer, default=0)
    source_type = Column(String(20))  # 'cluster', 'trend', 'topic'
    source_description = Column(String(500))  # Description of what was used
    source_posts = Column(Text)  # JSON array of post IDs used

    # Status
    is_published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime, nullable=True)
    platform = Column(String(50), nullable=True)  # Where it was published

    # Engagement (if tracked)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    # Temporal
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_format_created', 'format_type', 'created_at'),
        Index('idx_published_status', 'is_published', 'created_at'),
    )

    def __repr__(self):
        return f"<GeneratedContent {self.format_type}: {self.title[:50] if self.title else 'Untitled'}>"


# Database initialization
def init_universal_db(database_url='sqlite:///data/insights.db'):
    """Initialize database with universal models"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine
