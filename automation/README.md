# Automation Components

This directory contains components for automating content generation and posting.

## Components

### 1. TopicSelector (✓ Implemented)

Selects unique topics for content generation, ensuring variety and no repetition.

**Features:**
- Prevents topic repetition within configurable time window (default: 30 days)
- Prefers trending topics when available
- Tracks usage history in database
- Falls back to ad-hoc topic generation when topics table is not available
- Supports multiple selection strategies

**Usage:**
```python
from automation.topic_selector import TopicSelector
from storage.universal_database import UniversalDatabaseManager

db = UniversalDatabaseManager(DATABASE_URL)
selector = TopicSelector(db)

# Select next unique topic
topic = selector.select_next_topic(
    exclude_days=30,        # Don't repeat topics from last 30 days
    prefer_trending=True,   # Prefer trending topics
    min_posts=3            # Topic must have at least 3 posts
)

if topic:
    print(f"Selected topic: {topic['keywords']}")
    print(f"Posts to analyze: {topic['posts']}")

    # Generate content using this topic...

    # Mark as used after successful generation
    selector.mark_topic_used(topic, content_id)
```

**Topic Structure:**
```python
{
    'topic_id': int or None,           # ID from analytics (if available)
    'keywords': List[str],             # Keywords defining the topic
    'post_count': int,                 # Number of posts in topic
    'is_trending': bool,               # Whether topic is currently trending
    'posts': List[int],                # List of post IDs to analyze
    'avg_importance': float            # Average importance score
}
```

### 2. TelegramPoster (Planned)

Posts generated content to Telegram channels.

**Planned Features:**
- Async posting to multiple channels
- Message formatting for Telegram
- Media attachment support (images, videos)
- Error handling and retry logic
- Rate limiting compliance

**Planned Usage:**
```python
from automation.telegram_poster import TelegramPoster

poster = TelegramPoster(
    bot_token=TELEGRAM_BOT_TOKEN,
    channel_id=TELEGRAM_CHANNEL_ID
)

# Post content
result = await poster.post_content(
    content=generated_content,
    media_path=None  # Optional image/video
)
```

### 3. ReelGenerator (Planned)

Generates visual content (images/short videos) for social media reels.

**Planned Features:**
- Text-to-image generation using PIL
- Template-based design
- Multiple aspect ratios (1:1, 9:16, 16:9)
- Customizable styles and themes
- Optional: Video generation from images

**Planned Usage:**
```python
from automation.reel_generator import ReelGenerator

generator = ReelGenerator()

# Generate reel image
image_path = generator.generate_reel(
    title=content['title'],
    key_points=content['key_points'],
    style='modern',
    aspect_ratio='9:16'  # Instagram Reels, TikTok
)
```

### 4. AutoContentSystem (Planned)

Main orchestrator that coordinates all components for fully automated content pipeline.

**Planned Features:**
- Scheduled content generation
- End-to-end workflow orchestration
- Error handling and recovery
- Performance monitoring
- Configurable schedules

**Planned Usage:**
```python
from automation.auto_content_system import AutoContentSystem

# Initialize system
auto_system = AutoContentSystem(
    db_manager=db,
    content_generator=content_gen,
    topic_selector=selector,
    telegram_poster=poster,
    reel_generator=reel_gen
)

# Run once
await auto_system.generate_and_post()

# Or schedule (using APScheduler)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    auto_system.generate_and_post,
    'cron',
    hour=9,        # Daily at 9:00
    minute=0
)
scheduler.start()
```

## Database Schema

### UsedTopic Table

Tracks which topics have been used for content generation.

```sql
CREATE TABLE used_topics (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER,                    -- Reference to topics table
    keywords TEXT,                       -- JSON array of keywords
    keywords_hash VARCHAR(64),           -- SHA-256 hash for deduplication
    used_at TIMESTAMP,                   -- When it was used
    content_id INTEGER,                  -- Reference to generated_content
    post_count INTEGER,                  -- Number of posts in topic
    source_type VARCHAR(20)              -- 'topic', 'trend', 'cluster'
);

CREATE INDEX idx_keywords_hash_used ON used_topics(keywords_hash, used_at);
```

## Integration with Existing System

### 1. Content Generation Flow

```
TopicSelector.select_next_topic()
    ↓
ContentGenerator.generate_from_topic()
    ↓
Database.save_generated_content()
    ↓
TopicSelector.mark_topic_used()
```

### 2. Complete Automation Flow

```
Scheduler triggers every day at 9:00 AM
    ↓
TopicSelector selects unique topic
    ↓
ContentGenerator generates post
    ↓
Database saves content
    ↓
TopicSelector marks topic as used
    ↓
ReelGenerator creates image
    ↓
TelegramPoster posts to channel
    ↓
Database marks content as published
```

## Testing

Run the test suite:

```bash
python test_topic_selector.py
```

This will:
1. Initialize TopicSelector
2. Test topic selection
3. Test usage tracking
4. Show usage statistics
5. Demonstrate the API

## Next Steps

1. ✓ TopicSelector - Implemented and tested
2. ⏳ TelegramPoster - Next component to implement
3. ⏳ ReelGenerator - After TelegramPoster
4. ⏳ AutoContentSystem - Final orchestrator
5. ⏳ Scheduler integration in app_v2.py

## Configuration

Environment variables needed for full automation:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel

# Groq API (already configured)
GROQ_API_KEY=your_groq_key

# Automation settings
AUTO_GENERATE_ENABLED=true
AUTO_GENERATE_SCHEDULE='0 9 * * *'  # Cron format: Daily at 9 AM
TOPIC_EXCLUDE_DAYS=30
CONTENT_FORMAT=long_post
CONTENT_LANGUAGE=ru
```

## Architecture Principles

1. **Dependency Injection**: All components receive dependencies through constructors
2. **Loose Coupling**: Components don't directly depend on each other
3. **Single Responsibility**: Each component has one clear purpose
4. **Testability**: All components can be tested independently
5. **Error Handling**: Graceful degradation when components fail
6. **Logging**: Comprehensive logging for debugging and monitoring

## Example: Manual Content Generation with TopicSelector

```python
from storage.universal_database import UniversalDatabaseManager
from automation.topic_selector import TopicSelector
from analyzers.content_generator import ContentGenerator
import os

# Initialize components
DATABASE_URL = os.getenv('DATABASE_URL')
db = UniversalDatabaseManager(DATABASE_URL)
selector = TopicSelector(db)
generator = ContentGenerator(api_key=os.getenv('GROQ_API_KEY'))

# Select topic
topic = selector.select_next_topic(exclude_days=30, prefer_trending=True)

if not topic:
    print("No suitable topic found")
    exit(1)

print(f"Selected topic: {topic['keywords']}")

# Get posts for this topic
from storage.universal_models import UniversalPost

posts = db.session.query(UniversalPost).filter(
    UniversalPost.id.in_(topic['posts'])
).all()

# Generate content
content = generator.generate_from_topic(
    posts=posts,
    format_type='long_post',
    language='ru',
    tone='professional'
)

# Save to database
content_id = db.save_generated_content({
    'format': 'long_post',
    'language': 'ru',
    'tone': 'professional',
    'title': content.get('title'),
    'content': content['content'],
    'hashtags': content.get('hashtags', []),
    'key_points': content.get('key_points', []),
    'word_count': len(content['content']),
    'source_type': 'topic',
    'source_description': f"Topic: {', '.join(topic['keywords'][:3])}",
    'source_posts': topic['posts']
})

# Mark topic as used
selector.mark_topic_used(topic, content_id)

print(f"Content generated successfully! ID: {content_id}")
print(f"Title: {content.get('title')}")
print(f"Length: {len(content['content'])} characters")
```

This demonstrates the complete manual workflow that will be automated by AutoContentSystem.
