"""
Database models for storing parsed data
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class HNPost(Base):
    """Hacker News post (story/question)"""
    __tablename__ = 'hn_posts'

    id = Column(Integer, primary_key=True)
    hn_id = Column(Integer, unique=True, index=True)  # HN item ID
    title = Column(String(500))
    url = Column(String(1000), nullable=True)
    text = Column(Text, nullable=True)  # Self-post text
    author = Column(String(100))
    score = Column(Integer, default=0)
    post_type = Column(String(50))  # 'ask_hn', 'show_hn', 'new'
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    comments_count = Column(Integer, default=0)

    comments = relationship("HNComment", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HNPost {self.hn_id}: {self.title[:50]}>"


class HNComment(Base):
    """Hacker News comment"""
    __tablename__ = 'hn_comments'

    id = Column(Integer, primary_key=True)
    hn_id = Column(Integer, unique=True, index=True)
    post_id = Column(Integer, ForeignKey('hn_posts.id'))
    parent_id = Column(Integer, nullable=True)  # Parent comment ID
    author = Column(String(100))
    text = Column(Text)
    created_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("HNPost", back_populates="comments")

    def __repr__(self):
        return f"<HNComment {self.hn_id} by {self.author}>"


class Signal(Base):
    """Detected signals/patterns"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True)
    signal_type = Column(String(50))  # 'pain', 'language', 'solution', 'behavior'
    title = Column(String(500))
    description = Column(Text)
    source = Column(String(50))  # 'hacker_news', 'reddit', etc.
    frequency = Column(Integer, default=1)  # How many times mentioned
    keywords = Column(Text)  # JSON list of related keywords
    example_urls = Column(Text)  # JSON list of example URLs
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Signal {self.signal_type}: {self.title[:50]}>"


class ParserRun(Base):
    """Track parser execution history"""
    __tablename__ = 'parser_runs'

    id = Column(Integer, primary_key=True)
    source = Column(String(50))  # 'hacker_news'
    section = Column(String(50))  # 'ask', 'show', 'new'
    items_fetched = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20))  # 'running', 'success', 'failed'
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ParserRun {self.source}/{self.section} at {self.started_at}>"


# Database initialization
def init_db(database_url='sqlite:///data/insights.db'):
    """Initialize database and create tables"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
