"""
AI-powered analyzer using Groq API
- Summarization
- Insight extraction
- Categorization
- Sentiment analysis
- Technology/company detection
"""
from groq import Groq
from typing import Dict, List, Optional
import json


class AIAnalyzer:
    """AI-powered post analysis using Groq API"""

    def __init__(self, api_key: str):
        """
        Initialize AI Analyzer

        Args:
            api_key: Groq API key
        """
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"  # Fast and free

    def analyze_post(self, title: str, content: str) -> Dict:
        """
        Comprehensive AI analysis of a post

        Returns:
            {
                'summary': str,           # 1-sentence summary
                'category': str,          # problem/solution/product/question/discussion
                'sentiment': str,         # positive/negative/neutral
                'key_insights': [str],    # List of key insights
                'technologies': [str],    # Mentioned technologies
                'companies': [str],       # Mentioned companies
                'topics': [str]           # Main topics
            }
        """
        # Combine title and content
        full_text = f"Title: {title}\n\nContent: {content or 'No content'}"

        # Truncate if too long (max ~3000 tokens for speed)
        if len(full_text) > 12000:
            full_text = full_text[:12000] + "..."

        # Create comprehensive analysis prompt
        prompt = f"""Analyze this post and provide structured insights:

{full_text}

Provide analysis in JSON format:
{{
    "summary": "One sentence summary of the post",
    "category": "problem|solution|product|question|discussion",
    "sentiment": "positive|negative|neutral",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "technologies": ["tech1", "tech2"],
    "companies": ["company1", "company2"],
    "topics": ["topic1", "topic2"]
}}

Rules:
- summary: max 20 words
- key_insights: 2-5 most important takeaways
- technologies: programming languages, frameworks, tools mentioned
- companies: company/startup names mentioned
- topics: main themes discussed

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert analyst. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            # Sometimes LLM adds markdown code blocks, remove them
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)

            # Validate and clean
            return {
                'summary': result.get('summary', '')[:200],
                'category': result.get('category', 'discussion').lower(),
                'sentiment': result.get('sentiment', 'neutral').lower(),
                'key_insights': result.get('key_insights', [])[:5],
                'technologies': result.get('technologies', [])[:10],
                'companies': result.get('companies', [])[:10],
                'topics': result.get('topics', [])[:5]
            }

        except Exception as e:
            print(f"AI analysis error: {e}")
            return {
                'summary': '',
                'category': 'discussion',
                'sentiment': 'neutral',
                'key_insights': [],
                'technologies': [],
                'companies': [],
                'topics': []
            }

    def quick_summary(self, title: str, content: str) -> str:
        """
        Quick one-sentence summary

        Returns:
            One sentence summary
        """
        full_text = f"{title}. {content or ''}"
        if len(full_text) > 8000:
            full_text = full_text[:8000]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize in one concise sentence (max 20 words)."
                    },
                    {
                        "role": "user",
                        "content": full_text
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary error: {e}")
            return ""

    def categorize_post(self, title: str, content: str) -> str:
        """
        Categorize post into one of: problem, solution, product, question, discussion

        Returns:
            Category name
        """
        full_text = f"{title}. {content or ''}"[:2000]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Categorize as: problem, solution, product, question, or discussion. Return only the category word."
                    },
                    {
                        "role": "user",
                        "content": full_text
                    }
                ],
                temperature=0.2,
                max_tokens=10
            )

            category = response.choices[0].message.content.strip().lower()
            valid_categories = ['problem', 'solution', 'product', 'question', 'discussion']

            return category if category in valid_categories else 'discussion'
        except Exception as e:
            print(f"Categorization error: {e}")
            return 'discussion'

    def extract_insights(self, title: str, content: str, num_insights: int = 3) -> List[str]:
        """
        Extract key insights from post

        Returns:
            List of insights
        """
        full_text = f"{title}. {content or ''}"
        if len(full_text) > 8000:
            full_text = full_text[:8000]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Extract {num_insights} key insights/takeaways. Return as JSON array of strings."
                    },
                    {
                        "role": "user",
                        "content": full_text
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )

            result = response.choices[0].message.content.strip()

            # Try to parse as JSON
            if result.startswith('['):
                insights = json.loads(result)
                return insights[:num_insights]
            else:
                # Fallback: split by newlines
                return [line.strip('- ').strip() for line in result.split('\n') if line.strip()][:num_insights]

        except Exception as e:
            print(f"Insight extraction error: {e}")
            return []

    def batch_analyze_posts(self, posts: List[Dict]) -> List[Dict]:
        """
        Analyze multiple posts in batch

        Args:
            posts: List of dicts with 'title' and 'content'

        Returns:
            List of analysis results
        """
        results = []

        for post in posts:
            analysis = self.analyze_post(
                post.get('title', ''),
                post.get('content', '')
            )
            results.append({
                'post_id': post.get('id'),
                'analysis': analysis
            })

        return results
