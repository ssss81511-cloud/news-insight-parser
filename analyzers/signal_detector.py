"""
Signal detection and pattern analysis
Based on news_insight_agent.md specification
"""
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict
import re
from storage.database import DatabaseManager
from utils.helpers import clean_html, extract_keywords


class SignalDetector:
    """Detect patterns and signals from parsed content"""

    # Pain-related keywords
    PAIN_KEYWORDS = [
        'problem', 'issue', 'struggle', 'difficult', 'pain', 'challenge',
        'frustrated', 'hard', 'trouble', 'stuck', 'broken', 'slow',
        'expensive', 'complicated', 'confusing', 'annoying', 'lacking'
    ]

    # Solution indicators
    SOLUTION_KEYWORDS = [
        'built', 'created', 'made', 'solution', 'workaround', 'fixed',
        'solved', 'implemented', 'developed', 'tool', 'script', 'hack'
    ]

    def __init__(self, db: DatabaseManager):
        self.db = db

    def detect_all_signals(self, lookback_days: int = 7):
        """Run all signal detection algorithms"""
        print(f"Detecting signals from last {lookback_days} days...")

        self.detect_repeating_pains(lookback_days)
        self.detect_emerging_language(lookback_days)
        self.detect_solution_patterns(lookback_days)

        print("Signal detection complete!")

    def detect_repeating_pains(self, lookback_days: int = 7, min_mentions: int = 3):
        """
        Detect repeating pain points across posts and comments

        Signal Type: pain
        Focus: Problems mentioned by multiple founders
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get recent posts and comments
        posts = self.db.session.query(self.db.session.query(self.db.engine.table_names)).all()
        from storage.models import HNPost, HNComment

        # Collect all text content
        pain_contexts = []

        # Check posts
        posts = self.db.session.query(HNPost).filter(
            HNPost.fetched_at >= cutoff_date
        ).all()

        for post in posts:
            text = f"{post.title} {post.text or ''}"
            text_lower = text.lower()

            # Check for pain keywords
            for keyword in self.PAIN_KEYWORDS:
                if keyword in text_lower:
                    pain_contexts.append({
                        'text': clean_html(text)[:500],
                        'keyword': keyword,
                        'source': 'hacker_news',
                        'url': f"https://news.ycombinator.com/item?id={post.hn_id}",
                        'type': post.post_type
                    })
                    break

        # Check comments
        comments = self.db.session.query(HNComment).filter(
            HNComment.fetched_at >= cutoff_date
        ).all()

        for comment in comments:
            text_lower = comment.text.lower()

            for keyword in self.PAIN_KEYWORDS:
                if keyword in text_lower:
                    pain_contexts.append({
                        'text': clean_html(comment.text)[:500],
                        'keyword': keyword,
                        'source': 'hacker_news',
                        'url': f"https://news.ycombinator.com/item?id={comment.hn_id}",
                        'author': comment.author
                    })
                    break

        # Extract common pain topics
        all_keywords = []
        for ctx in pain_contexts:
            keywords = extract_keywords(ctx['text'])
            all_keywords.extend(keywords)

        # Find frequent pain topics
        keyword_counts = Counter(all_keywords)
        common_pains = keyword_counts.most_common(20)

        # Create signals for common pains
        for keyword, count in common_pains:
            if count >= min_mentions:
                # Find example URLs
                examples = [ctx['url'] for ctx in pain_contexts if keyword in ctx['text'].lower()][:3]

                signal_data = {
                    'signal_type': 'pain',
                    'title': f"Repeating pain: {keyword}",
                    'description': f"Mentioned {count} times in discussions. Common pain point among founders.",
                    'source': 'hacker_news',
                    'frequency': count,
                    'keywords': keyword,
                    'example_urls': ', '.join(examples),
                    'first_seen': datetime.utcnow(),
                    'last_seen': datetime.utcnow(),
                    'is_active': True
                }

                self.db.add_signal(signal_data)

        print(f"Detected {len(common_pains)} pain signals")

    def detect_emerging_language(self, lookback_days: int = 7, min_frequency: int = 5):
        """
        Detect new or emerging terms and language shifts

        Signal Type: language
        Focus: New terminology, metaphors, word usage
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        from storage.models import HNPost

        # Get recent posts
        posts = self.db.session.query(HNPost).filter(
            HNPost.fetched_at >= cutoff_date
        ).all()

        # Extract all keywords
        all_keywords = []
        for post in posts:
            text = f"{post.title} {post.text or ''}"
            keywords = extract_keywords(text)
            all_keywords.extend(keywords)

        # Find trending terms
        keyword_counts = Counter(all_keywords)

        # Focus on tech/business terms (longer words, capitalized)
        emerging_terms = []
        for keyword, count in keyword_counts.most_common(30):
            if count >= min_frequency and len(keyword) >= 4:
                # Check if it looks like a tech term (contains capitals, numbers, or is compound)
                if keyword[0].isupper() or '-' in keyword or any(c.isdigit() for c in keyword):
                    emerging_terms.append((keyword, count))

        # Create signals for emerging language
        for term, count in emerging_terms[:10]:
            signal_data = {
                'signal_type': 'language',
                'title': f"Emerging term: {term}",
                'description': f"Used {count} times recently. Potential new terminology or trend.",
                'source': 'hacker_news',
                'frequency': count,
                'keywords': term,
                'example_urls': '',
                'first_seen': datetime.utcnow(),
                'last_seen': datetime.utcnow(),
                'is_active': True
            }

            self.db.add_signal(signal_data)

        print(f"Detected {len(emerging_terms)} language signals")

    def detect_solution_patterns(self, lookback_days: int = 7, min_occurrences: int = 2):
        """
        Detect common solution patterns and workarounds

        Signal Type: solution
        Focus: Similar tools/approaches appearing independently
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        from storage.models import HNPost, HNComment

        # Collect solution mentions
        solution_contexts = []

        # Check posts
        posts = self.db.session.query(HNPost).filter(
            HNPost.fetched_at >= cutoff_date
        ).all()

        for post in posts:
            text = f"{post.title} {post.text or ''}"
            text_lower = text.lower()

            # Check for solution keywords
            for keyword in self.SOLUTION_KEYWORDS:
                if keyword in text_lower:
                    solution_contexts.append({
                        'text': clean_html(text)[:500],
                        'keyword': keyword,
                        'url': f"https://news.ycombinator.com/item?id={post.hn_id}"
                    })
                    break

        # Extract common solution topics
        all_keywords = []
        for ctx in solution_contexts:
            keywords = extract_keywords(ctx['text'])
            all_keywords.extend(keywords)

        # Find frequent solution patterns
        keyword_counts = Counter(all_keywords)
        common_solutions = keyword_counts.most_common(15)

        # Create signals
        for keyword, count in common_solutions:
            if count >= min_occurrences:
                examples = [ctx['url'] for ctx in solution_contexts if keyword in ctx['text'].lower()][:3]

                signal_data = {
                    'signal_type': 'solution',
                    'title': f"Solution pattern: {keyword}",
                    'description': f"Appears in {count} solution discussions. Common approach to solving problems.",
                    'source': 'hacker_news',
                    'frequency': count,
                    'keywords': keyword,
                    'example_urls': ', '.join(examples),
                    'first_seen': datetime.utcnow(),
                    'last_seen': datetime.utcnow(),
                    'is_active': True
                }

                self.db.add_signal(signal_data)

        print(f"Detected {len(common_solutions)} solution pattern signals")
