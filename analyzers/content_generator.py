"""
Content Generator for Social Media
Generates posts from analyzed data in different formats
"""
from groq import Groq
from typing import Dict, List, Optional
import json
from datetime import datetime, timezone


class ContentGenerator:
    """
    Generates social media content from analyzed posts

    Formats:
    - long_post: Detailed analysis (1000-1500 chars) for LinkedIn/Instagram carousel
    - reel: Short punchy post (100-200 chars) for Instagram Reels/TikTok
    - thread: Twitter/X thread (5-7 tweets)
    """

    def __init__(self, api_key: str, db_manager):
        """
        Initialize Content Generator

        Args:
            api_key: Groq API key
            db_manager: Database manager instance
        """
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Updated model (llama-3.1-70b is deprecated)
        self.db = db_manager

    def generate_from_cluster(self,
                             cluster_posts: List,
                             format_type: str = 'long_post',
                             tone: str = 'professional',
                             language: str = 'en') -> Dict:
        """
        Generate content from a cluster of related posts

        Args:
            cluster_posts: List of UniversalPost objects from same cluster
            format_type: 'long_post', 'reel', or 'thread'
            tone: 'professional', 'casual', 'inspirational'
            language: 'en' or 'ru'

        Returns:
            {
                'content': str (or list of str for thread),
                'title': str,
                'hashtags': [str],
                'source_posts': [int],  # post IDs used
                'format': str,
                'word_count': int
            }
        """
        if not cluster_posts:
            raise ValueError("No posts provided for content generation")

        # Prepare context from posts
        context = self._prepare_context(cluster_posts)

        # Select appropriate prompt based on format
        if format_type == 'long_post':
            prompt = self._build_long_post_prompt(context, tone, language)
        elif format_type == 'reel':
            prompt = self._build_reel_prompt(context, tone, language)
        elif format_type == 'thread':
            prompt = self._build_thread_prompt(context, tone, language)
        else:
            raise ValueError(f"Unknown format: {format_type}")

        # Generate content
        generated = self._call_ai(prompt)

        # Post-process
        result = self._parse_generated_content(generated, format_type)
        result['source_posts'] = [p.id for p in cluster_posts]
        result['format'] = format_type

        return result

    def generate_from_trend(self,
                           trend_keyword: str,
                           lookback_days: int = 7,
                           format_type: str = 'long_post',
                           tone: str = 'professional',
                           language: str = 'en') -> Dict:
        """
        Generate content about a trending keyword

        Args:
            trend_keyword: Trending keyword to write about
            lookback_days: Days to look back for posts
            format_type: Content format
            tone: Writing tone
            language: Output language

        Returns:
            Generated content dict
        """
        from storage.universal_models import UniversalPost
        from datetime import timedelta

        # Find posts mentioning this keyword
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).all()

        # Filter posts containing the keyword
        relevant_posts = [
            p for p in posts
            if trend_keyword.lower() in f"{p.title} {p.content or ''}".lower()
        ]

        if not relevant_posts:
            raise ValueError(f"No posts found for keyword: {trend_keyword}")

        # Sort by importance
        relevant_posts.sort(key=lambda x: x.importance_score, reverse=True)

        # Take top 10 most important
        top_posts = relevant_posts[:10]

        return self.generate_from_cluster(top_posts, format_type, tone, language)

    def generate_from_topic(self,
                           topic_keywords: List[str],
                           lookback_days: int = 7,
                           format_type: str = 'long_post',
                           tone: str = 'professional',
                           language: str = 'en') -> Dict:
        """
        Generate content about a detected topic

        Args:
            topic_keywords: List of keywords defining the topic
            lookback_days: Days to look back
            format_type: Content format
            tone: Writing tone
            language: Output language

        Returns:
            Generated content dict
        """
        from storage.universal_models import UniversalPost
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        posts = self.db.session.query(UniversalPost).filter(
            UniversalPost.created_at >= cutoff_date
        ).all()

        # Score posts by topic relevance
        scored_posts = []
        for post in posts:
            text = f"{post.title} {post.content or ''}".lower()
            score = sum(1 for keyword in topic_keywords if keyword.lower() in text)
            if score > 0:
                scored_posts.append((post, score))

        if not scored_posts:
            raise ValueError(f"No posts found for topic: {', '.join(topic_keywords[:3])}")

        # Sort by topic relevance, then importance
        scored_posts.sort(key=lambda x: (x[1], x[0].importance_score), reverse=True)

        # Take top 10
        top_posts = [p for p, score in scored_posts[:10]]

        return self.generate_from_cluster(top_posts, format_type, tone, language)

    def _prepare_context(self, posts: List) -> Dict:
        """Prepare context from posts for AI"""
        # Extract key information
        titles = [p.title for p in posts]
        summaries = [p.ai_summary for p in posts if p.ai_summary]
        insights = []
        technologies = []
        companies = []

        for post in posts:
            if post.ai_insights:
                try:
                    insights.extend(json.loads(post.ai_insights))
                except:
                    pass

            if post.ai_technologies:
                try:
                    technologies.extend(json.loads(post.ai_technologies))
                except:
                    pass

            if post.ai_companies:
                try:
                    companies.extend(json.loads(post.ai_companies))
                except:
                    pass

        # Get unique items
        technologies = list(set(technologies))[:10]
        companies = list(set(companies))[:10]

        # Sample content from top posts
        sample_content = []
        for post in posts[:5]:  # Top 5 posts
            if post.content:
                sample_content.append({
                    'title': post.title,
                    'snippet': post.content[:300],
                    'source': post.source,
                    'url': post.source_url
                })

        return {
            'post_count': len(posts),
            'titles': titles[:10],
            'summaries': summaries[:10],
            'insights': insights[:15],
            'technologies': technologies,
            'companies': companies,
            'samples': sample_content
        }

    def _build_long_post_prompt(self, context: Dict, tone: str, language: str) -> str:
        """Build prompt for long-form post generation"""
        lang_instruction = "in English" if language == 'en' else "на русском языке"

        prompt = f"""You are a professional content creator writing {lang_instruction}.

Based on this data from {context['post_count']} startup/tech posts:

Key Insights:
{json.dumps(context['insights'][:10], indent=2)}

Technologies mentioned: {', '.join(context['technologies'])}
Companies mentioned: {', '.join(context['companies'])}

Sample posts:
{json.dumps(context['samples'][:3], indent=2)}

Create a compelling LinkedIn/Instagram post (1000-1500 characters) with this structure:

1. Hook (attention-grabbing first line)
2. Context (what's happening in the industry)
3. Analysis (key insights with specific examples)
4. Takeaway (actionable conclusion)
5. 5-7 relevant hashtags

Tone: {tone}
Include specific examples and data points from the source posts.
Make it engaging and valuable for founders/entrepreneurs.

Return ONLY valid JSON:
{{
    "title": "Short catchy title",
    "content": "Full post text (1000-1500 chars)",
    "hashtags": ["hashtag1", "hashtag2", ...],
    "key_points": ["point1", "point2", "point3"]
}}"""

        return prompt

    def _build_reel_prompt(self, context: Dict, tone: str, language: str) -> str:
        """Build prompt for short-form reel/story generation"""
        lang_instruction = "in English" if language == 'en' else "на русском языке"

        prompt = f"""You are a viral content creator writing {lang_instruction}.

Based on insights from {context['post_count']} tech/startup posts:

Top Insights:
{json.dumps(context['insights'][:5], indent=2)}

Technologies: {', '.join(context['technologies'][:5])}

Create a short, punchy post for Instagram Reels/TikTok (100-200 characters total):

Requirements:
- Strong hook in first line (shocking stat, question, or bold claim)
- One powerful insight
- Call to action or thought-provoking ending
- Tone: {tone}
- Use emojis strategically (2-3 max)

Return ONLY valid JSON:
{{
    "content": "Full reel text (100-200 chars)",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}"""

        return prompt

    def _build_thread_prompt(self, context: Dict, tone: str, language: str) -> str:
        """Build prompt for Twitter/X thread generation"""
        lang_instruction = "in English" if language == 'en' else "на русском языке"

        prompt = f"""You are a Twitter/X thought leader writing {lang_instruction}.

Based on {context['post_count']} startup/tech posts:

Insights:
{json.dumps(context['insights'][:10], indent=2)}

Technologies: {', '.join(context['technologies'])}
Companies: {', '.join(context['companies'])}

Create a Twitter/X thread (5-7 tweets):

Tweet 1: Hook (surprising stat, bold claim, or question)
Tweets 2-5: Key insights with examples (one insight per tweet)
Tweet 6: Actionable takeaway
Tweet 7: Call to action + hashtags

Each tweet: max 280 characters
Tone: {tone}
Make it engaging and retweetable

Return ONLY valid JSON:
{{
    "tweets": [
        "Tweet 1 text",
        "Tweet 2 text",
        "Tweet 3 text",
        "Tweet 4 text",
        "Tweet 5 text",
        "Tweet 6 text",
        "Tweet 7 text"
    ],
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}"""

        return prompt

    def _call_ai(self, prompt: str) -> str:
        """Call Groq API to generate content"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert content creator. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # Higher creativity for content generation
            max_tokens=2000
        )

        return response.choices[0].message.content.strip()

    def _parse_generated_content(self, ai_response: str, format_type: str) -> Dict:
        """Parse AI response and extract content"""
        # Remove markdown code blocks if present
        if ai_response.startswith("```"):
            ai_response = ai_response.split("```")[1]
            if ai_response.startswith("json"):
                ai_response = ai_response[4:]
            ai_response = ai_response.strip()

        try:
            parsed = json.loads(ai_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response: {e}\n{ai_response}")

        # Format-specific processing
        if format_type == 'thread':
            content = parsed.get('tweets', [])
            word_count = sum(len(tweet) for tweet in content)
        else:
            content = parsed.get('content', '')
            word_count = len(content)

        return {
            'content': content,
            'title': parsed.get('title', ''),
            'hashtags': parsed.get('hashtags', []),
            'key_points': parsed.get('key_points', []),
            'word_count': word_count
        }
