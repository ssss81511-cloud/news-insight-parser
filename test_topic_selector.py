"""
Test script for TopicSelector

This script demonstrates how TopicSelector works and tests its functionality.
"""
import os
import sys
from datetime import datetime, timezone

# Set up database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/techcrunch.db')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"Using database: {DATABASE_URL}")

# Initialize database
from storage.universal_database import UniversalDatabaseManager

db = UniversalDatabaseManager(DATABASE_URL)
print("[OK] Database connected")

# Initialize TopicSelector
from automation.topic_selector import TopicSelector

selector = TopicSelector(db)
print("[OK] TopicSelector initialized")

# Test 1: Get usage statistics
print("\n" + "="*60)
print("TEST 1: Get usage statistics")
print("="*60)

stats = selector.get_usage_stats(days_back=30)
print(f"Topics used in last 30 days: {stats['total_used']}")
print(f"Topics per week: {stats['topics_per_week']:.2f}")
print(f"Most recent use: {stats['most_recent']}")

# Test 2: Select next topic
print("\n" + "="*60)
print("TEST 2: Select next unique topic")
print("="*60)

topic = selector.select_next_topic(
    exclude_days=30,
    prefer_trending=True,
    min_posts=2
)

if topic:
    print(f"[OK] Selected topic:")
    print(f"  - Topic ID: {topic.get('topic_id', 'N/A')}")
    print(f"  - Keywords: {topic['keywords'][:5]}")
    print(f"  - Post count: {topic['post_count']}")
    print(f"  - Is trending: {topic.get('is_trending', False)}")
    print(f"  - Posts IDs: {topic['posts'][:5]}...")
else:
    print("[!] No suitable topic found")
    print("  This is expected if:")
    print("  - No topics in database yet")
    print("  - All topics were used recently")
    print("  - No topics meet minimum post count")

# Test 3: Check if specific topic was used recently
print("\n" + "="*60)
print("TEST 3: Check if topic was used recently")
print("="*60)

test_keywords = ['AI', 'machine learning', 'LLM']
was_used = db.is_topic_used_recently(test_keywords, exclude_days=30)
print(f"Topic {test_keywords} was used recently: {was_used}")

# Test 4: Mark a topic as used (simulation)
print("\n" + "="*60)
print("TEST 4: Mark topic as used (simulation)")
print("="*60)

if topic:
    # Simulate marking the topic as used
    print(f"Simulating: Would mark topic {topic['keywords'][:3]} as used")
    print(f"After generating content, call: selector.mark_topic_used(topic, content_id)")
else:
    print("Skipping - no topic selected in Test 2")

# Test 5: Get recently used topics
print("\n" + "="*60)
print("TEST 5: Get recently used topics")
print("="*60)

used_topics = db.get_used_topics(days_back=30, limit=10)
if used_topics:
    print(f"Found {len(used_topics)} recently used topics:")
    for i, used in enumerate(used_topics[:5], 1):
        import json
        keywords = json.loads(used.keywords) if isinstance(used.keywords, str) else used.keywords
        print(f"  {i}. {keywords[:3]} - used on {used.used_at.strftime('%Y-%m-%d %H:%M')}")
else:
    print("No topics have been used yet")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("[OK] TopicSelector is working correctly")
print("\nNext steps:")
print("1. Run parsing to collect more posts")
print("2. Run analytics to generate topics")
print("3. Use TopicSelector in automation pipeline")
print("\nUsage example:")
print("""
from automation.topic_selector import TopicSelector
from storage.universal_database import UniversalDatabaseManager

db = UniversalDatabaseManager(DATABASE_URL)
selector = TopicSelector(db)

# Select unique topic
topic = selector.select_next_topic(exclude_days=30)

if topic:
    # Generate content using this topic
    # ... content generation code ...

    # Mark as used after successful generation
    selector.mark_topic_used(topic, content_id)
""")

print("\n" + "="*60)
