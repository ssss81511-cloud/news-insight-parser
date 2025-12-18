"""
Database operations and utilities
"""
from sqlalchemy.orm import Session
from storage.models import HNPost, HNComment, Signal, ParserRun, init_db, get_session
from datetime import datetime
from typing import List, Optional


class DatabaseManager:
    """Manage database operations"""

    def __init__(self, database_url='sqlite:///data/insights.db'):
        self.engine = init_db(database_url)
        self.session = get_session(self.engine)

    def add_hn_post(self, post_data: dict) -> HNPost:
        """Add or update HN post"""
        existing = self.session.query(HNPost).filter_by(hn_id=post_data['hn_id']).first()

        if existing:
            # Update existing post
            for key, value in post_data.items():
                setattr(existing, key, value)
            existing.fetched_at = datetime.utcnow()
            post = existing
        else:
            # Create new post
            post = HNPost(**post_data)
            self.session.add(post)

        self.session.commit()
        return post

    def add_hn_comment(self, comment_data: dict) -> HNComment:
        """Add or update HN comment"""
        existing = self.session.query(HNComment).filter_by(hn_id=comment_data['hn_id']).first()

        if existing:
            for key, value in comment_data.items():
                setattr(existing, key, value)
            comment = existing
        else:
            comment = HNComment(**comment_data)
            self.session.add(comment)

        self.session.commit()
        return comment

    def add_signal(self, signal_data: dict) -> Signal:
        """Add or update signal"""
        signal = Signal(**signal_data)
        self.session.add(signal)
        self.session.commit()
        return signal

    def start_parser_run(self, source: str, section: str) -> ParserRun:
        """Start tracking parser run"""
        run = ParserRun(
            source=source,
            section=section,
            status='running',
            started_at=datetime.utcnow()
        )
        self.session.add(run)
        self.session.commit()
        return run

    def finish_parser_run(self, run_id: int, items_fetched: int, status: str = 'success', error: str = None):
        """Finish tracking parser run"""
        run = self.session.query(ParserRun).filter_by(id=run_id).first()
        if run:
            run.items_fetched = items_fetched
            run.finished_at = datetime.utcnow()
            run.status = status
            run.error_message = error
            self.session.commit()

    def get_recent_posts(self, limit: int = 50, post_type: Optional[str] = None) -> List[HNPost]:
        """Get recent posts"""
        query = self.session.query(HNPost).order_by(HNPost.fetched_at.desc())
        if post_type:
            query = query.filter_by(post_type=post_type)
        return query.limit(limit).all()

    def get_recent_signals(self, limit: int = 20) -> List[Signal]:
        """Get recent signals"""
        return self.session.query(Signal).filter_by(is_active=True).order_by(Signal.last_seen.desc()).limit(limit).all()

    def get_parser_runs(self, limit: int = 10) -> List[ParserRun]:
        """Get recent parser runs"""
        return self.session.query(ParserRun).order_by(ParserRun.started_at.desc()).limit(limit).all()

    def get_stats(self) -> dict:
        """Get overall statistics"""
        return {
            'total_posts': self.session.query(HNPost).count(),
            'total_comments': self.session.query(HNComment).count(),
            'total_signals': self.session.query(Signal).filter_by(is_active=True).count(),
            'ask_hn_count': self.session.query(HNPost).filter_by(post_type='ask_hn').count(),
            'show_hn_count': self.session.query(HNPost).filter_by(post_type='show_hn').count(),
            'new_count': self.session.query(HNPost).filter_by(post_type='new').count(),
        }

    def close(self):
        """Close database session"""
        self.session.close()
