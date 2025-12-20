# AutoContentSystem Integration Guide

This guide shows how to integrate AutoContentSystem into your Flask app for automated daily content generation and posting.

## Overview

AutoContentSystem orchestrates all automation components:
1. TopicSelector - Selects unique topics
2. ContentGenerator - Generates AI content
3. ReelGenerator - Creates images
4. TelegramPoster - Posts to Telegram
5. Database - Tracks everything

## Quick Start

### 1. Basic Usage

```python
import asyncio
from storage.universal_database import UniversalDatabaseManager
from automation.topic_selector import TopicSelector
from automation.telegram_poster import TelegramPoster
from automation.reel_generator import create_reel_generator
from automation.auto_content_system import AutoContentSystem
from analyzers.content_generator import ContentGenerator

# Initialize components
db = UniversalDatabaseManager(DATABASE_URL)
topic_selector = TopicSelector(db)
content_generator = ContentGenerator(api_key=GROQ_API_KEY)
reel_generator = create_reel_generator()
telegram_poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)

# Create AutoContentSystem
auto_system = AutoContentSystem(
    db_manager=db,
    content_generator=content_generator,
    topic_selector=topic_selector,
    telegram_poster=telegram_poster,
    reel_generator=reel_generator
)

# Run once
result = await auto_system.generate_and_post()

if result['success']:
    print(f"Content posted! Message ID: {result['message_id']}")
else:
    print(f"Failed: {result['error']}")
```

### 2. Configuration

Customize behavior with config dictionary:

```python
auto_system = AutoContentSystem(
    db_manager=db,
    content_generator=content_generator,
    topic_selector=topic_selector,
    telegram_poster=telegram_poster,
    reel_generator=reel_generator,
    config={
        # Topic selection
        'topic_exclude_days': 30,       # Don't repeat topics from last 30 days
        'topic_prefer_trending': True,  # Prefer trending topics
        'topic_min_posts': 3,           # Min posts required for a topic

        # Content generation
        'content_format': 'long_post',  # 'long_post', 'reel', 'thread'
        'content_language': 'ru',       # 'ru' or 'en'
        'content_tone': 'professional', # 'professional', 'casual', 'inspirational'

        # Reel generation
        'reel_aspect_ratio': 'reel',    # 'square', 'reel', 'story', 'landscape', 'twitter'
        'reel_style': 'modern',         # 'modern', 'professional', 'vibrant', 'minimal', 'dark'

        # Features
        'enable_reel': True,            # Generate images
        'enable_telegram': True,        # Post to Telegram
        'max_retries': 3                # Retry attempts
    }
)
```

## Integration with Flask App

### Option 1: Manual Trigger (API Endpoint)

Add an endpoint to trigger content generation manually:

```python
# app_v2.py

from automation.auto_content_system import sync_generate_and_post

# Initialize auto_system once at app startup
auto_system = AutoContentSystem(...)

@app.route('/api/auto-generate', methods=['POST'])
def auto_generate():
    """Manual trigger for automated content generation"""
    try:
        result = sync_generate_and_post(auto_system)

        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'content_id': result.get('content_id'),
            'message_id': result.get('message_id'),
            'error': result.get('error'),
            'timestamp': result.get('timestamp').isoformat() if result.get('timestamp') else None
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

### Option 2: Scheduled Execution (APScheduler)

Run automatically on a schedule:

```python
# app_v2.py

from apscheduler.schedulers.background import BackgroundScheduler
from automation.auto_content_system import sync_generate_and_post
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()

# Initialize auto_system
auto_system = AutoContentSystem(...)

def scheduled_content_generation():
    """
    Scheduled job for automated content generation

    This runs on a schedule (e.g., daily at 9 AM)
    """
    logger.info("Starting scheduled content generation...")

    try:
        result = sync_generate_and_post(auto_system)

        if result['success']:
            logger.info(f"Content generated successfully! Content ID: {result['content_id']}, Message ID: {result['message_id']}")
        else:
            logger.error(f"Content generation failed: {result['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in scheduled job: {e}", exc_info=True)

# Schedule job - Daily at 9:00 AM
scheduler.add_job(
    func=scheduled_content_generation,
    trigger='cron',
    hour=9,
    minute=0,
    id='daily_content_generation',
    name='Generate and post daily content',
    replace_existing=True
)

# Start scheduler when Flask app starts
scheduler.start()

# Shutdown scheduler when app stops
import atexit
atexit.register(lambda: scheduler.shutdown())
```

### Option 3: Multiple Schedules

Post different content at different times:

```python
# Morning post - trending topics
scheduler.add_job(
    func=lambda: sync_generate_and_post(AutoContentSystem(..., config={
        'topic_prefer_trending': True,
        'content_format': 'long_post',
        'reel_style': 'modern'
    })),
    trigger='cron',
    hour=9,
    minute=0,
    id='morning_post'
)

# Evening post - thread format
scheduler.add_job(
    func=lambda: sync_generate_and_post(AutoContentSystem(..., config={
        'content_format': 'thread',
        'reel_aspect_ratio': 'square',
        'reel_style': 'vibrant'
    })),
    trigger='cron',
    hour=18,
    minute=0,
    id='evening_post'
)
```

## Complete Flask Integration Example

```python
# app_v2.py

import os
from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import logging

from storage.universal_database import UniversalDatabaseManager
from automation.topic_selector import TopicSelector
from automation.telegram_poster import TelegramPoster
from automation.reel_generator import create_reel_generator
from automation.auto_content_system import AutoContentSystem, sync_generate_and_post
from analyzers.content_generator import ContentGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/techcrunch.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
AUTO_GENERATE_ENABLED = os.getenv('AUTO_GENERATE_ENABLED', 'false').lower() == 'true'
AUTO_GENERATE_HOUR = int(os.getenv('AUTO_GENERATE_HOUR', '9'))

# Initialize components
db = UniversalDatabaseManager(DATABASE_URL)
topic_selector = TopicSelector(db)
content_generator = ContentGenerator(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
reel_generator = create_reel_generator()

# Initialize Telegram poster if configured
telegram_poster = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
    telegram_poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
    logger.info("Telegram poster initialized")

# Initialize AutoContentSystem
auto_system = None
if content_generator:
    auto_system = AutoContentSystem(
        db_manager=db,
        content_generator=content_generator,
        topic_selector=topic_selector,
        telegram_poster=telegram_poster,
        reel_generator=reel_generator,
        config={
            'topic_exclude_days': 30,
            'topic_prefer_trending': True,
            'topic_min_posts': 3,
            'content_format': 'long_post',
            'content_language': 'ru',
            'content_tone': 'professional',
            'reel_aspect_ratio': 'reel',
            'reel_style': 'modern',
            'enable_reel': True,
            'enable_telegram': telegram_poster is not None,
        }
    )
    logger.info("AutoContentSystem initialized")

# Scheduled job function
def scheduled_content_generation():
    """Run automated content generation"""
    if not auto_system:
        logger.error("AutoContentSystem not initialized")
        return

    logger.info("Starting scheduled content generation...")
    result = sync_generate_and_post(auto_system)

    if result['success']:
        logger.info(f"SUCCESS - Content ID: {result['content_id']}, Message: {result['message_id']}")
    else:
        logger.error(f"FAILED - {result['error']}")

# Initialize scheduler if enabled
if AUTO_GENERATE_ENABLED and auto_system:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=scheduled_content_generation,
        trigger='cron',
        hour=AUTO_GENERATE_HOUR,
        minute=0,
        id='daily_content_generation',
        name='Daily automated content generation'
    )
    scheduler.start()
    logger.info(f"Scheduler started - Will run daily at {AUTO_GENERATE_HOUR}:00")

    import atexit
    atexit.register(lambda: scheduler.shutdown())

# API endpoint for manual trigger
@app.route('/api/auto-generate', methods=['POST'])
def trigger_auto_generate():
    """Manually trigger automated content generation"""
    if not auto_system:
        return jsonify({'status': 'error', 'message': 'AutoContentSystem not configured'}), 500

    result = sync_generate_and_post(auto_system)

    return jsonify({
        'status': 'success' if result['success'] else 'error',
        'content_id': result.get('content_id'),
        'message_id': result.get('message_id'),
        'image_path': result.get('image_path'),
        'error': result.get('error'),
        'timestamp': result.get('timestamp').isoformat() if result.get('timestamp') else None
    })

# API endpoint for system stats
@app.route('/api/auto-stats', methods=['GET'])
def get_auto_stats():
    """Get automation system statistics"""
    if not auto_system:
        return jsonify({'status': 'error', 'message': 'AutoContentSystem not configured'}), 500

    stats = auto_system.get_stats()
    return jsonify({'status': 'success', 'stats': stats})

# ... rest of your Flask app ...

if __name__ == '__main__':
    app.run(debug=True)
```

## Environment Variables

Add to `.env` or Render environment variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host/db
GROQ_API_KEY=your_groq_api_key

# Optional - for Telegram posting
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel

# Optional - automation settings
AUTO_GENERATE_ENABLED=true
AUTO_GENERATE_HOUR=9  # Hour to run (0-23)
```

## Monitoring

### Check Scheduler Status

```python
@app.route('/api/scheduler-status', methods=['GET'])
def scheduler_status():
    """Check scheduler status"""
    if not scheduler:
        return jsonify({'status': 'disabled'})

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return jsonify({
        'status': 'running',
        'jobs': jobs
    })
```

### View Logs

On Render, check logs for scheduled execution:
```bash
render logs -a your-app-name
```

Look for messages like:
```
[INFO] Starting scheduled content generation...
[INFO] SUCCESS - Content ID: 123, Message: 456
```

## Troubleshooting

### Scheduler not running

- Check `AUTO_GENERATE_ENABLED=true` is set
- Verify GROQ_API_KEY is configured
- Check logs for initialization errors

### Content not generating

- Ensure there are posts in database (run parsers first)
- Check GROQ_API_KEY is valid
- Verify topics exist (run analytics)
- Look for errors in logs

### Telegram posting failing

- Verify TELEGRAM_BOT_TOKEN is correct
- Check bot is admin in channel
- Verify TELEGRAM_CHANNEL_ID format (@channel or -100xxx)
- Test connection with test script

### Images not generating

- Pillow may not be installed (check requirements.txt)
- On Render (Linux), Pillow should work
- Check logs for image generation errors
- Falls back gracefully if image generation fails

## Best Practices

1. **Start with manual testing**
   - Test with `/api/auto-generate` endpoint first
   - Verify each component works
   - Check Telegram channel for posts

2. **Use appropriate schedules**
   - Daily posting: Once per day is usually enough
   - Avoid peak hours (when manual posts are common)
   - Consider time zones of your audience

3. **Monitor regularly**
   - Check logs daily for first week
   - Set up alerts for failures
   - Review generated content quality

4. **Adjust configuration**
   - Start with `topic_exclude_days=30`
   - Adjust based on available topics
   - Try different styles/formats

5. **Database maintenance**
   - Run parsers regularly to get new data
   - Run analytics to generate topics
   - Clean up old data periodically

## Next Steps

After integration:

1. Run parsers to collect posts
2. Run analytics to generate topics
3. Test manual generation endpoint
4. Enable scheduler if ready
5. Monitor first few automated posts
6. Adjust configuration as needed
