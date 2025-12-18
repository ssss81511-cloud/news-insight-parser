"""
Advanced analytics module for insights detection
- Word frequency analysis
- Topic clustering
- Trend detection
- Visualization data generation
"""
from typing import List, Dict, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np


class InsightsAnalyzer:
    """
    Analyzes posts to extract insights:
    1. Word frequency analysis
    2. Topic clustering
    3. Trend detection over time
    4. Key themes identification
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        """Load common stopwords to filter out"""
        return {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'was', 'with', 'this', 'that', 'from', 'have', 'has', 'had',
            'been', 'were', 'will', 'would', 'could', 'should', 'may', 'might',
            'what', 'which', 'who', 'when', 'where', 'why', 'how',
            'just', 'like', 'get', 'got', 'make', 'made', 'use', 'used',
            'does', 'did', 'doing', 'think', 'know', 'want', 'need',
            'see', 'look', 'take', 'come', 'give', 'find', 'tell',
            'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call'
        }

    def get_top_posts(self, lookback_days: int = 7, top_n: int = 20) -> List[Dict]:
        """
        Get top posts by importance score

        Returns:
            List of top posts with metadata
        """
        from storage.universal_models import UniversalPost

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).order_by(
            UniversalPost.importance_score.desc()
        ).limit(top_n).all()

        top_posts = []
        for post in posts:
            top_posts.append({
                'title': post.title,
                'source': post.source,
                'score': post.score,
                'comments_count': post.comments_count,
                'importance_score': round(post.importance_score, 1),
                'url': post.source_url,
                'created_at': post.created_at.isoformat() if post.created_at else None
            })

        return top_posts

    def _extract_words(self, text: str, min_length: int = 4) -> List[str]:
        """Extract meaningful words from text"""
        if not text:
            return []

        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]{' + str(min_length) + r',}\b', text)

        # Filter stopwords
        return [w for w in words if w not in self.stopwords]

    def detect_topics(self, lookback_days: int = 7,
                     n_topics: int = 5,
                     n_words: int = 10) -> List[Dict]:
        """
        Detect main topics using LDA (Latent Dirichlet Allocation)

        Returns:
            [
                {
                    'topic_id': int,
                    'keywords': [str, ...],
                    'post_count': int
                },
                ...
            ]
        """
        from storage.universal_models import UniversalPost

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).all()

        if len(posts) < n_topics:
            return []

        # Prepare documents
        documents = []
        for post in posts:
            text = f"{post.title} {post.content or ''}"
            documents.append(text)

        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            min_df=2,
            max_df=0.8
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(documents)

            # LDA topic modeling
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=10
            )
            lda.fit(tfidf_matrix)

            # Extract topics
            feature_names = vectorizer.get_feature_names_out()
            topics = []

            for topic_idx, topic in enumerate(lda.components_):
                top_indices = topic.argsort()[-n_words:][::-1]
                keywords = [feature_names[i] for i in top_indices]

                topics.append({
                    'topic_id': topic_idx + 1,
                    'keywords': keywords,
                    'post_count': int((lda.transform(tfidf_matrix)[:, topic_idx] > 0.3).sum())
                })

            return topics
        except Exception as e:
            print(f"Topic detection error: {e}")
            return []

    def cluster_similar_posts(self, lookback_days: int = 7,
                             n_clusters: int = 8) -> List[Dict]:
        """
        Cluster similar posts using K-Means

        Returns:
            [
                {
                    'cluster_id': int,
                    'size': int,
                    'top_keywords': [str, ...],
                    'sample_titles': [str, ...]
                },
                ...
            ]
        """
        from storage.universal_models import UniversalPost

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).all()

        if len(posts) < n_clusters:
            return []

        # Prepare documents
        documents = []
        post_objects = []

        for post in posts:
            text = f"{post.title} {post.content or ''}"
            documents.append(text)
            post_objects.append(post)

        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=300,
            stop_words='english',
            min_df=1,
            max_df=0.9
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(documents)

            # K-Means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)

            # Analyze clusters
            clusters = []
            feature_names = vectorizer.get_feature_names_out()

            for cluster_id in range(n_clusters):
                # Get posts in this cluster
                cluster_posts = [post_objects[i] for i, label in enumerate(cluster_labels) if label == cluster_id]

                if not cluster_posts:
                    continue

                # Get cluster center keywords
                cluster_center = kmeans.cluster_centers_[cluster_id]
                top_indices = cluster_center.argsort()[-10:][::-1]
                top_keywords = [feature_names[i] for i in top_indices]

                # Sample titles
                sample_titles = [p.title for p in cluster_posts[:5]]

                clusters.append({
                    'cluster_id': cluster_id + 1,
                    'size': len(cluster_posts),
                    'top_keywords': top_keywords,
                    'sample_titles': sample_titles,
                    'avg_score': round(sum(p.score for p in cluster_posts) / len(cluster_posts), 1)
                })

            # Sort by size
            clusters.sort(key=lambda x: x['size'], reverse=True)

            return clusters
        except Exception as e:
            print(f"Clustering error: {e}")
            return []

    def detect_trends(self, lookback_days: int = 30) -> Dict:
        """
        Detect trending topics over time

        Returns:
            {
                'trending_keywords': [
                    {
                        'keyword': str,
                        'current_count': int,
                        'previous_count': int,
                        'growth_rate': float
                    },
                    ...
                ],
                'timeline': {
                    'dates': [str, ...],
                    'post_counts': [int, ...],
                    'avg_scores': [float, ...]
                }
            }
        """
        from storage.universal_models import UniversalPost

        # Split into current and previous periods
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=lookback_days // 2)
        previous_start = now - timedelta(days=lookback_days)

        # Get posts for both periods
        current_posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= current_start
        ).all()

        previous_posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= previous_start,
            UniversalPost.created_at < current_start
        ).all()

        # Extract keywords from both periods
        current_words = Counter()
        previous_words = Counter()

        for post in current_posts:
            text = f"{post.title} {post.content or ''}"
            words = self._extract_words(text, min_length=5)
            current_words.update(words)

        for post in previous_posts:
            text = f"{post.title} {post.content or ''}"
            words = self._extract_words(text, min_length=5)
            previous_words.update(words)

        # Calculate growth rates
        trending = []
        for word, current_count in current_words.most_common(100):
            if current_count < 3:  # Minimum threshold
                continue

            previous_count = previous_words.get(word, 0)

            # Calculate growth rate
            if previous_count > 0:
                growth_rate = ((current_count - previous_count) / previous_count) * 100
            else:
                growth_rate = 100.0  # New word

            if growth_rate > 20:  # Only show significant growth
                trending.append({
                    'keyword': word,
                    'current_count': current_count,
                    'previous_count': previous_count,
                    'growth_rate': round(growth_rate, 1)
                })

        # Sort by growth rate
        trending.sort(key=lambda x: x['growth_rate'], reverse=True)

        # Generate timeline data
        timeline = self._generate_timeline(lookback_days)

        return {
            'trending_keywords': trending[:20],
            'timeline': timeline
        }

    def _generate_timeline(self, lookback_days: int = 30) -> Dict:
        """Generate timeline data for visualization"""
        from storage.universal_models import UniversalPost

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=lookback_days)

        # Get all posts in range
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= start_date
        ).all()

        # Group by date
        daily_data = defaultdict(lambda: {'count': 0, 'scores': []})

        for post in posts:
            date_key = post.created_at.date().isoformat()
            daily_data[date_key]['count'] += 1
            daily_data[date_key]['scores'].append(post.score)

        # Sort by date
        sorted_dates = sorted(daily_data.keys())

        dates = []
        post_counts = []
        avg_scores = []

        for date in sorted_dates:
            data = daily_data[date]
            dates.append(date)
            post_counts.append(data['count'])
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            avg_scores.append(round(avg_score, 1))

        return {
            'dates': dates,
            'post_counts': post_counts,
            'avg_scores': avg_scores
        }

    def get_source_distribution(self, lookback_days: int = 7) -> Dict:
        """
        Get distribution of posts by source

        Returns:
            {
                'sources': [str, ...],
                'counts': [int, ...],
                'percentages': [float, ...]
            }
        """
        from storage.universal_models import UniversalPost

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).all()

        # Count by source
        source_counts = Counter()
        for post in posts:
            source_counts[post.source] += 1

        total = sum(source_counts.values())

        sources = []
        counts = []
        percentages = []

        for source, count in source_counts.most_common():
            sources.append(source)
            counts.append(count)
            percentages.append(round((count / total) * 100, 1) if total > 0 else 0)

        return {
            'sources': sources,
            'counts': counts,
            'percentages': percentages
        }
