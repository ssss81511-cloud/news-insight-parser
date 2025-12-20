"""
Test script for AutoContentSystem

This script tests the complete automation workflow from topic selection
to content generation to posting.

IMPORTANT: Set environment variables before running:
- DATABASE_URL (or will use default SQLite)
- GROQ_API_KEY (required for content generation)
- TELEGRAM_BOT_TOKEN (optional, for Telegram posting)
- TELEGRAM_CHANNEL_ID (optional, for Telegram posting)
"""
import os
import asyncio
from datetime import datetime

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/techcrunch.db')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

print("="*60)
print("AUTO CONTENT SYSTEM TEST")
print("="*60)

# Check requirements
if not GROQ_API_KEY:
    print("\n[ERROR] GROQ_API_KEY not set!")
    print("Set it with: export GROQ_API_KEY='your_key'")
    exit(1)

print(f"\n[CONFIG] Database: {DATABASE_URL}")
print(f"[CONFIG] GROQ API: {'Set' if GROQ_API_KEY else 'Not set'}")
print(f"[CONFIG] Telegram: {'Enabled' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID else 'Disabled'}")

async def run_tests():
    """Run all AutoContentSystem tests"""

    # Initialize components
    print("\n" + "="*60)
    print("TEST 1: Initialize components")
    print("="*60)

    from storage.universal_database import UniversalDatabaseManager
    from automation.topic_selector import TopicSelector
    from analyzers.content_generator import ContentGenerator
    from automation.reel_generator import create_reel_generator
    from automation.auto_content_system import AutoContentSystem

    try:
        # Database
        db = UniversalDatabaseManager(DATABASE_URL)
        print("[OK] Database connected")

        # Topic Selector
        topic_selector = TopicSelector(db)
        print("[OK] TopicSelector initialized")

        # Content Generator
        content_generator = ContentGenerator(api_key=GROQ_API_KEY)
        print("[OK] ContentGenerator initialized")

        # Reel Generator
        reel_generator = create_reel_generator(output_dir='test_auto_reels')
        print("[OK] ReelGenerator initialized")

        # Telegram Poster (optional)
        telegram_poster = None
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            from automation.telegram_poster import TelegramPoster
            telegram_poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
            print("[OK] TelegramPoster initialized")
        else:
            print("[WARNING] TelegramPoster not configured - skipping")

        # Auto Content System
        auto_system = AutoContentSystem(
            db_manager=db,
            content_generator=content_generator,
            topic_selector=topic_selector,
            telegram_poster=telegram_poster,
            reel_generator=reel_generator,
            config={
                'topic_exclude_days': 30,
                'topic_prefer_trending': True,
                'topic_min_posts': 2,  # Lower for testing
                'content_format': 'long_post',
                'content_language': 'ru',
                'content_tone': 'professional',
                'reel_aspect_ratio': 'square',  # Faster to generate
                'reel_style': 'modern',
                'enable_reel': True,
                'enable_telegram': bool(telegram_poster),
            }
        )
        print("[OK] AutoContentSystem initialized")

    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 2: Test components individually
    print("\n" + "="*60)
    print("TEST 2: Test individual components")
    print("="*60)

    try:
        test_results = await auto_system.test_components()
        print("\n[OK] Component tests completed")
    except Exception as e:
        print(f"[ERROR] Component tests failed: {e}")

    # Test 3: Get system stats
    print("\n" + "="*60)
    print("TEST 3: Get system statistics")
    print("="*60)

    try:
        stats = auto_system.get_stats()
        print("\nSystem Statistics:")
        print(f"  Topics used (30 days): {stats.get('topics_used_30d', 0)}")
        print(f"  Topics per week: {stats.get('topics_per_week', 0):.2f}")
        print(f"  Total generated: {stats.get('total_generated', 0)}")
        print(f"  Total published: {stats.get('total_published', 0)}")
        print(f"  Publish rate: {stats.get('publish_rate', 0):.1%}")
        print(f"  Last run: {stats.get('last_run', 'Never')}")
    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")

    # Test 4: Run complete workflow (DRY RUN)
    print("\n" + "="*60)
    print("TEST 4: Run complete workflow (may take 60-90 seconds)")
    print("="*60)

    user_input = input("\nRun complete workflow? This will:\n"
                      "  1. Select a unique topic\n"
                      "  2. Generate content using AI\n"
                      "  3. Create a reel image\n"
                      "  4. Post to Telegram (if configured)\n"
                      "\nProceed? (y/n): ")

    if user_input.lower() != 'y':
        print("[SKIPPED] User chose not to run workflow")
        print("\nTo run workflow manually later:")
        print("  result = await auto_system.generate_and_post()")
        return

    try:
        print("\n[INFO] Starting workflow...")
        print("[INFO] This may take 60-90 seconds for AI content generation...")

        start_time = datetime.now()
        result = await auto_system.generate_and_post()
        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n[INFO] Workflow completed in {elapsed:.1f} seconds")

        # Display results
        print("\n" + "="*60)
        print("WORKFLOW RESULTS")
        print("="*60)

        if result['success']:
            print("[OK] Workflow succeeded!")
            print(f"\nGenerated content:")
            print(f"  Content ID: {result.get('content_id')}")
            print(f"  Topic: {result.get('topic', {}).get('keywords', [])[:3]}")
            print(f"  Image: {result.get('image_path', 'None')}")
            print(f"  Telegram Message ID: {result.get('message_id', 'Not posted')}")
            print(f"  Timestamp: {result.get('timestamp')}")

            # Show the topic that was used
            if result.get('topic'):
                topic = result['topic']
                print(f"\nTopic details:")
                print(f"  Keywords: {topic.get('keywords', [])[:5]}")
                print(f"  Post count: {topic.get('post_count', 0)}")
                print(f"  Trending: {topic.get('is_trending', False)}")

        else:
            print("[FAIL] Workflow failed")
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"[ERROR] Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\n[OK] All tests completed!")
    print("\nAutoContentSystem is ready for:")
    print("  - Manual execution: await auto_system.generate_and_post()")
    print("  - Scheduled execution: Integration with APScheduler")
    print("  - API endpoint: Integration in Flask app")
    print("\nNext steps:")
    print("  1. Configure Telegram credentials (if not done)")
    print("  2. Set up scheduler for daily automation")
    print("  3. Monitor logs and adjust configuration")

# Run tests
if __name__ == '__main__':
    print("\nStarting tests...")
    asyncio.run(run_tests())
    print("\nTests finished!")
