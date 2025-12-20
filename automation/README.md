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

### 2. TelegramPoster (✓ Implemented)

Posts generated content to Telegram channels.

**Features:**
- ✓ Async posting with proper error handling
- ✓ Automatic retry logic with exponential backoff
- ✓ Rate limiting compliance (handles RetryAfter)
- ✓ HTML/Markdown message formatting
- ✓ Media support (images)
- ✓ Thread support (multiple messages)
- ✓ Message length handling (4096 char limit)
- ✓ Connection testing

**Usage:**
```python
from automation.telegram_poster import TelegramPoster
import asyncio

# Initialize
poster = TelegramPoster(
    bot_token=TELEGRAM_BOT_TOKEN,
    channel_id=TELEGRAM_CHANNEL_ID,
    max_retries=3
)

# Test connection
is_connected = await poster.test_connection()

# Post single message
result = await poster.post_content(
    content={
        'title': 'Post Title',
        'content': 'Post content here',
        'hashtags': ['#AI', '#Tech'],
        'format_type': 'long_post'
    },
    media_path='path/to/image.jpg'  # Optional
)

# Post thread (multiple messages)
result = await poster.post_content(
    content={
        'content': [
            'First tweet',
            'Second tweet',
            'Third tweet'
        ],
        'hashtags': ['#Thread'],
        'format_type': 'thread'
    }
)

# Synchronous wrapper (for Flask routes)
from automation.telegram_poster import sync_post

result = sync_post(
    bot_token=TELEGRAM_BOT_TOKEN,
    channel_id=TELEGRAM_CHANNEL_ID,
    content=generated_content
)
```

**Result Structure:**
```python
{
    'success': bool,
    'message_id': int,           # Telegram message ID
    'message_ids': List[int],    # For threads
    'error': str or None,
    'posted_at': datetime
}
```

### 3. ReelGenerator (✓ Implemented)

Generates visual content (images) for social media reels using PIL/Pillow.

**Features:**
- ✓ Text-to-image generation using Pillow
- ✓ 5 professional color schemes (modern, professional, vibrant, minimal, dark)
- ✓ 5 aspect ratios (square, reel, story, landscape, twitter)
- ✓ Automatic text wrapping
- ✓ Key points with styled bullet points
- ✓ Customizable footer text
- ✓ Mock mode for development when Pillow unavailable
- ✓ High-quality JPEG output (95% quality)

**Usage:**
```python
from automation.reel_generator import create_reel_generator

# Initialize (auto-detects if Pillow is available)
generator = create_reel_generator(output_dir='generated_reels')

# Generate from title and key points
image_path = generator.generate_reel(
    title='AI Trends 2025',
    key_points=[
        'LLMs continue to evolve',
        'AI agents becoming autonomous',
        'Open source gaining traction'
    ],
    aspect_ratio='reel',  # 1080x1920 for Instagram Reels/TikTok
    style='modern',
    footer_text='@YourChannel'
)

# Or generate directly from content dictionary
image_path = generator.generate_from_content(
    content=generated_content,
    aspect_ratio='square',  # 1080x1080
    style='professional'
)

# Get available options
styles = generator.get_available_styles()
# ['modern', 'professional', 'vibrant', 'minimal', 'dark']

ratios = generator.get_available_aspect_ratios()
# ['square', 'reel', 'story', 'landscape', 'twitter']
```

**Aspect Ratios:**
- `square`: 1080x1080 (Instagram post, Facebook)
- `reel`: 1080x1920 (Instagram Reels, TikTok, YouTube Shorts)
- `story`: 1080x1920 (Instagram/Facebook Stories)
- `landscape`: 1920x1080 (YouTube, LinkedIn)
- `twitter`: 1200x675 (Twitter/X)

**Color Schemes:**
- `modern`: Dark blue-gray with indigo accents
- `professional`: Clean white with blue accents
- `vibrant`: Purple with yellow/orange highlights
- `minimal`: Light gray with subtle slate tones
- `dark`: Black with red/green accents

### 4. AutoContentSystem (✓ Implemented)

Main orchestrator that coordinates all components for fully automated content pipeline.

**Features:**
- ✓ End-to-end workflow orchestration
- ✓ 7-step automated process
- ✓ Comprehensive error handling with graceful degradation
- ✓ Detailed logging at each step
- ✓ Configuration system
- ✓ Statistics tracking
- ✓ Component testing
- ✓ Async and sync wrappers

**Workflow Steps:**
1. Select unique topic (TopicSelector)
2. Fetch posts for topic (Database)
3. Generate content (ContentGenerator)
4. Save content to database
5. Mark topic as used
6. Generate reel image (ReelGenerator)
7. Post to Telegram (TelegramPoster)

**Usage:**
```python
from automation.auto_content_system import AutoContentSystem, sync_generate_and_post

# Initialize system
auto_system = AutoContentSystem(
    db_manager=db,
    content_generator=content_generator,
    topic_selector=topic_selector,
    telegram_poster=telegram_poster,
    reel_generator=reel_generator,
    config={
        'topic_exclude_days': 30,
        'topic_prefer_trending': True,
        'content_format': 'long_post',
        'content_language': 'ru',
        'reel_style': 'modern',
        'enable_reel': True,
        'enable_telegram': True
    }
)

# Async usage
result = await auto_system.generate_and_post()

# Sync usage (for Flask)
result = sync_generate_and_post(auto_system)

# Check result
if result['success']:
    print(f"Posted! Content ID: {result['content_id']}, Message ID: {result['message_id']}")
else:
    print(f"Failed: {result['error']}")

# Get statistics
stats = auto_system.get_stats()

# Test components
test_results = await auto_system.test_components()
```

**Integration with APScheduler:**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=lambda: sync_generate_and_post(auto_system),
    trigger='cron',
    hour=9,
    minute=0,
    id='daily_content'
)
scheduler.start()
```

**Result Structure:**
```python
{
    'success': bool,
    'content_id': int,           # Database ID of generated content
    'message_id': int,           # Telegram message ID
    'image_path': str,           # Path to generated reel
    'topic': Dict,               # Topic that was used
    'error': str or None,
    'timestamp': datetime
}
```

**Error Handling:**
- Topic selection failure: Returns error immediately
- No posts found: Returns error with topic info
- Content generation failure: Returns error
- Reel generation failure: Continues without image (graceful)
- Telegram posting failure: Content saved but not posted (can retry manually)

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
