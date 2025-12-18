"""
Enhanced signal detector with:
- Prioritization
- Context preservation
- Cross-source correlation
- Trend analysis
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import re
import json
from storage.universal_database import UniversalDatabaseManager
from storage.universal_models import UniversalPost, UniversalComment
from utils.helpers import clean_html


class EnhancedSignalDetector:
    """
    Enhanced signal detection with context and prioritization
    """

    # Pain-related keywords
    PAIN_KEYWORDS = [
        'problem', 'issue', 'struggle', 'difficult', 'pain', 'challenge',
        'frustrated', 'hard', 'trouble', 'stuck', 'broken', 'slow',
        'expensive', 'complicated', 'confusing', 'annoying', 'lacking',
        'nightmare', 'terrible', 'awful', 'hate', 'sucks'
    ]

    # Solution indicators
    SOLUTION_KEYWORDS = [
        'built', 'created', 'made', 'solution', 'workaround', 'fixed',
        'solved', 'implemented', 'developed', 'tool', 'script', 'hack',
        'automated', 'optimized', 'improved'
    ]

    # Emerging tech terms patterns
    TECH_PATTERNS = [
        r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase (NextJS, TypeScript)
        r'\b[a-z]+-[a-z]+\b',  # kebab-case (open-source, real-time)
        r'\b\w+\.\w+\b',  # dotted (node.js, web3.0)
    ]

    def __init__(self, db: UniversalDatabaseManager):
        self.db = db

    def detect_all_signals(self, lookback_days: int = 7, min_mentions: int = 3):
        """Run all signal detection with enhanced features"""
        print(f"🔍 Detecting signals from last {lookback_days} days...")

        # Detect each type
        pain_signals = self.detect_repeating_pains(lookback_days, min_mentions)
        language_signals = self.detect_emerging_language(lookback_days)
        solution_signals = self.detect_solution_patterns(lookback_days)

        # Merge cross-source signals
        self._merge_cross_source_signals()

        print(f"✅ Detection complete!")
        print(f"   - {len(pain_signals)} pain signals")
        print(f"   - {len(language_signals)} language signals")
        print(f"   - {len(solution_signals)} solution signals")

    def detect_repeating_pains(self, lookback_days: int = 7,
                               min_mentions: int = 3) -> List[Dict]:
        """
        Detect repeating pain points WITH CONTEXT

        Returns list of pain signals with:
        - Frequency
        - Priority
        - Context snippets (actual quotes)
        - Example URLs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get recent posts
        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.fetched_at >= cutoff_date
        ).all()

        # Collect pains with context
        pain_mentions = defaultdict(list)

        for post in posts:
            text = f"{post.title} {post.content or ''}"
            text_lower = text.lower()

            # Check for pain keywords
            for keyword in self.PAIN_KEYWORDS:
                if keyword in text_lower:
                    # Extract context around the pain keyword
                    context = self._extract_context(text, keyword, window=100)

                    pain_mentions[keyword].append({
                        'context': context,
                        'url': post.source_url,
                        'source': post.source,
                        'score': post.score,
                        'timestamp': post.created_at
                    })

        # Also check comments
        comments = self.db.session.query(UniversalComment).filter(
            UniversalComment.fetched_at >= cutoff_date
        ).all()

        for comment in comments:
            text_lower = comment.content.lower()

            for keyword in self.PAIN_KEYWORDS:
                if keyword in text_lower:
                    context = self._extract_context(comment.content, keyword, window=100)

                    # Get parent post URL
                    post = self.db.session.query(UniversalPost).filter_by(
                        id=comment.post_id
                    ).first()

                    if post:
                        pain_mentions[keyword].append({
                            'context': context,
                            'url': post.source_url,
                            'source': post.source,
                            'score': comment.score if comment.score else 0,
                            'timestamp': comment.created_at
                        })

        # Extract topics from context
        pain_topics = self._extract_pain_topics(pain_mentions)

        # Create signals for high-frequency pains
        signals = []
        for topic, mentions in pain_topics.items():
            if len(mentions) >= min_mentions:
                # Calculate growth rate
                growth_rate = self._calculate_growth_rate(mentions, lookback_days)

                # Get unique sources
                sources = list(set(m['source'] for m in mentions))
                is_cross_source = len(sources) > 1

                # Select best context snippets
                top_contexts = sorted(mentions, key=lambda x: x['score'], reverse=True)[:5]
                context_snippets = [m['context'] for m in top_contexts]
                example_urls = [m['url'] for m in top_contexts]

                # Calculate confidence
                confidence = self._calculate_confidence(mentions, lookback_days)

                signal_data = {
                    'signal_type': 'pain',
                    'title': f"Repeating pain: {topic}",
                    'description': f"Mentioned {len(mentions)} times across {len(sources)} source(s). {self._describe_pain(context_snippets)}",
                    'frequency': len(mentions),
                    'growth_rate': growth_rate,
                    'velocity': growth_rate / max(lookback_days, 1),
                    'sources': json.dumps(sources),
                    'keywords': topic,
                    'context_snippets': json.dumps(context_snippets),
                    'example_urls': json.dumps(example_urls),
                    'is_cross_source': is_cross_source,
                    'confidence_score': confidence,
                    'first_seen': min(m['timestamp'] for m in mentions),
                    'last_seen': max(m['timestamp'] for m in mentions),
                }

                signal = self.db.add_enhanced_signal(signal_data)
                signals.append(signal)

        return signals

    def _extract_context(self, text: str, keyword: str, window: int = 100) -> str:
        """
        Extract context around a keyword

        Args:
            text: Full text
            keyword: Keyword to find
            window: Characters before/after keyword

        Returns:
            Context snippet
        """
        text = clean_html(text)
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        pos = text_lower.find(keyword_lower)
        if pos == -1:
            return text[:200]

        start = max(0, pos - window)
        end = min(len(text), pos + len(keyword) + window)

        snippet = text[start:end].strip()

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _extract_pain_topics(self, pain_mentions: Dict) -> Dict:
        """
        Extract actual topics from pain contexts

        Instead of just "problem", extract "pricing problem", "API problem", etc.
        """
        topics = defaultdict(list)

        for keyword, mentions in pain_mentions.items():
            for mention in mentions:
                # Extract 2-3 words around the pain keyword
                context = mention['context'].lower()
                words = context.split()

                # Find pain keyword in words
                try:
                    idx = next(i for i, w in enumerate(words) if keyword in w)

                    # Get surrounding words
                    topic_words = []
                    # 2 words before
                    if idx > 0:
                        topic_words.append(words[idx-1])
                    # The keyword itself
                    topic_words.append(keyword)
                    # 1 word after
                    if idx < len(words) - 1:
                        topic_words.append(words[idx+1])

                    topic = ' '.join(topic_words)
                    topics[topic].append(mention)
                except StopIteration:
                    topics[keyword].append(mention)

        return topics

    def _describe_pain(self, contexts: List[str]) -> str:
        """Generate human-readable description from contexts"""
        # Extract common themes
        all_words = []
        for context in contexts[:3]:  # Top 3 contexts
            words = [w for w in context.lower().split() if len(w) > 4]
            all_words.extend(words)

        common_words = Counter(all_words).most_common(3)

        if common_words:
            themes = [w for w, c in common_words]
            return f"Common themes: {', '.join(themes)}"
        return ""

    def detect_emerging_language(self, lookback_days: int = 7) -> List[Dict]:
        """Detect emerging terms with context"""
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.fetched_at >= cutoff_date
        ).all()

        # Collect all text
        term_mentions = defaultdict(list)

        for post in posts:
            text = f"{post.title} {post.content or ''}"

            # Find tech terms using patterns
            for pattern in self.TECH_PATTERNS:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) >= 4:  # Minimum 4 characters
                        context = self._extract_context(text, match, window=80)
                        term_mentions[match].append({
                            'context': context,
                            'url': post.source_url,
                            'source': post.source,
                            'timestamp': post.created_at
                        })

        # Create signals for frequent terms
        signals = []
        for term, mentions in term_mentions.items():
            if len(mentions) >= 5:  # Minimum 5 mentions
                sources = list(set(m['source'] for m in mentions))
                growth_rate = self._calculate_growth_rate(mentions, lookback_days)

                signal_data = {
                    'signal_type': 'language',
                    'title': f"Emerging term: {term}",
                    'description': f"Used {len(mentions)} times recently. Potential new trend or technology.",
                    'frequency': len(mentions),
                    'growth_rate': growth_rate,
                    'velocity': growth_rate / max(lookback_days, 1),
                    'sources': json.dumps(sources),
                    'keywords': term,
                    'context_snippets': json.dumps([m['context'] for m in mentions[:5]]),
                    'example_urls': json.dumps([m['url'] for m in mentions[:5]]),
                    'is_cross_source': len(sources) > 1,
                    'confidence_score': min(len(mentions) * 10, 100),
                    'first_seen': min(m['timestamp'] for m in mentions),
                    'last_seen': max(m['timestamp'] for m in mentions),
                }

                signal = self.db.add_enhanced_signal(signal_data)
                signals.append(signal)

        return signals

    def detect_solution_patterns(self, lookback_days: int = 7) -> List[Dict]:
        """Detect solution patterns with context"""
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.fetched_at >= cutoff_date
        ).all()

        solution_mentions = defaultdict(list)

        for post in posts:
            text = f"{post.title} {post.content or ''}"
            text_lower = text.lower()

            for keyword in self.SOLUTION_KEYWORDS:
                if keyword in text_lower:
                    context = self._extract_context(text, keyword, window=100)
                    solution_mentions[keyword].append({
                        'context': context,
                        'url': post.source_url,
                        'source': post.source,
                        'timestamp': post.created_at
                    })

        # Extract solution topics
        solution_topics = self._extract_pain_topics(solution_mentions)

        signals = []
        for topic, mentions in solution_topics.items():
            if len(mentions) >= 2:
                sources = list(set(m['source'] for m in mentions))
                growth_rate = self._calculate_growth_rate(mentions, lookback_days)

                signal_data = {
                    'signal_type': 'solution',
                    'title': f"Solution pattern: {topic}",
                    'description': f"Appears in {len(mentions)} discussions. Common approach to solving problems.",
                    'frequency': len(mentions),
                    'growth_rate': growth_rate,
                    'velocity': growth_rate / max(lookback_days, 1),
                    'sources': json.dumps(sources),
                    'keywords': topic,
                    'context_snippets': json.dumps([m['context'] for m in mentions[:5]]),
                    'example_urls': json.dumps([m['url'] for m in mentions[:5]]),
                    'is_cross_source': len(sources) > 1,
                    'confidence_score': min(len(mentions) * 15, 100),
                    'first_seen': min(m['timestamp'] for m in mentions),
                    'last_seen': max(m['timestamp'] for m in mentions),
                }

                signal = self.db.add_enhanced_signal(signal_data)
                signals.append(signal)

        return signals

    def _calculate_growth_rate(self, mentions: List[Dict], lookback_days: int) -> float:
        """
        Calculate growth rate of mentions over time

        Returns:
            Growth rate (positive = growing, negative = declining)
        """
        if len(mentions) < 2:
            return 0.0

        # Split into first half and second half
        sorted_mentions = sorted(mentions, key=lambda x: x['timestamp'])
        mid_point = len(sorted_mentions) // 2

        first_half = sorted_mentions[:mid_point]
        second_half = sorted_mentions[mid_point:]

        # Growth rate = (second_half - first_half) / first_half
        if len(first_half) == 0:
            return 0.0

        growth = (len(second_half) - len(first_half)) / len(first_half)
        return growth

    def _calculate_confidence(self, mentions: List[Dict], lookback_days: int) -> float:
        """Calculate confidence score for a signal"""
        # Factors:
        # - Number of mentions
        # - Spread across time
        # - Multiple sources

        score = 0.0

        # Frequency (40 points)
        score += min(len(mentions) * 4, 40)

        # Time spread (30 points)
        if len(mentions) > 1:
            timestamps = [m['timestamp'] for m in mentions]
            time_span = (max(timestamps) - min(timestamps)).days
            time_score = min(time_span / lookback_days * 30, 30)
            score += time_score

        # Multiple sources (30 points)
        sources = set(m['source'] for m in mentions)
        score += min(len(sources) * 15, 30)

        return min(score, 100)

    def _merge_cross_source_signals(self):
        """
        Merge similar signals from different sources

        Example: "pricing problem" on HN + "pricing issues" on Reddit
        → 1 signal with combined frequency
        """
        # Get all active signals
        from storage.universal_models import EnhancedSignal

        signals = self.db.session.query(EnhancedSignal).filter_by(
            is_active=True
        ).all()

        # Group by signal type
        by_type = defaultdict(list)
        for signal in signals:
            by_type[signal.signal_type].append(signal)

        # Within each type, find similar signals
        for signal_type, type_signals in by_type.items():
            merged_ids = set()

            for i, signal1 in enumerate(type_signals):
                if signal1.id in merged_ids:
                    continue

                similar_signals = []

                for j, signal2 in enumerate(type_signals):
                    if i != j and signal2.id not in merged_ids:
                        # Check if keywords are similar
                        similarity = self._keyword_similarity(
                            signal1.keywords,
                            signal2.keywords
                        )

                        if similarity > 0.7:
                            similar_signals.append(signal2)

                # Merge similar signals
                if similar_signals:
                    self._merge_signals(signal1, similar_signals)
                    merged_ids.update(s.id for s in similar_signals)

        self.db.session.commit()

    def _keyword_similarity(self, keywords1: str, keywords2: str) -> float:
        """Calculate similarity between two keyword strings"""
        words1 = set(keywords1.lower().split())
        words2 = set(keywords2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _merge_signals(self, primary_signal, similar_signals):
        """Merge similar signals into primary signal"""
        # Combine frequencies
        total_frequency = primary_signal.frequency
        for signal in similar_signals:
            total_frequency += signal.frequency

        # Combine sources
        primary_sources = json.loads(primary_signal.sources) if primary_signal.sources else []
        for signal in similar_signals:
            signal_sources = json.loads(signal.sources) if signal.sources else []
            primary_sources.extend(signal_sources)
        primary_sources = list(set(primary_sources))

        # Combine contexts
        primary_contexts = json.loads(primary_signal.context_snippets) if primary_signal.context_snippets else []
        for signal in similar_signals:
            signal_contexts = json.loads(signal.context_snippets) if signal.context_snippets else []
            primary_contexts.extend(signal_contexts)

        # Combine URLs
        primary_urls = json.loads(primary_signal.example_urls) if primary_signal.example_urls else []
        for signal in similar_signals:
            signal_urls = json.loads(signal.example_urls) if signal.example_urls else []
            primary_urls.extend(signal_urls)

        # Update primary signal
        primary_signal.frequency = total_frequency
        primary_signal.sources = json.dumps(primary_sources)
        primary_signal.is_cross_source = len(primary_sources) > 1
        primary_signal.context_snippets = json.dumps(primary_contexts[:10])  # Keep top 10
        primary_signal.example_urls = json.dumps(primary_urls[:10])
        primary_signal.related_signal_ids = json.dumps([s.id for s in similar_signals])

        # Recalculate importance
        primary_signal.importance_score = self.db._calculate_signal_importance(primary_signal)
        primary_signal.priority = self.db._determine_priority(
            primary_signal.importance_score,
            primary_signal.frequency
        )

        # Deactivate merged signals
        for signal in similar_signals:
            signal.is_active = False
