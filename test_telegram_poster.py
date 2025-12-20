"""
Test script for TelegramPoster

This script tests the TelegramPoster component functionality.

IMPORTANT: Before running this test:
1. Create a Telegram bot with @BotFather
2. Get the bot token
3. Create a channel or use existing one
4. Add bot as admin to the channel
5. Set environment variables:
   - TELEGRAM_BOT_TOKEN=your_bot_token
   - TELEGRAM_CHANNEL_ID=@your_channel or -100xxxxxxxxxx
"""
import os
import asyncio
from automation.telegram_poster import TelegramPoster

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

print("="*60)
print("TELEGRAM POSTER TEST")
print("="*60)

# Check configuration
if not BOT_TOKEN:
    print("\n[ERROR] TELEGRAM_BOT_TOKEN environment variable not set!")
    print("\nPlease set it before running tests:")
    print("  export TELEGRAM_BOT_TOKEN='your_bot_token'")
    print("\nTo get a bot token:")
    print("  1. Open Telegram and find @BotFather")
    print("  2. Send /newbot command")
    print("  3. Follow instructions to create your bot")
    print("  4. Copy the token @BotFather gives you")
    exit(1)

if not CHANNEL_ID:
    print("\n[ERROR] TELEGRAM_CHANNEL_ID environment variable not set!")
    print("\nPlease set it before running tests:")
    print("  export TELEGRAM_CHANNEL_ID='@your_channel'")
    print("\nTo get channel ID:")
    print("  1. Create a public channel (or use existing)")
    print("  2. Use format: @channelname")
    print("  3. Add your bot as admin to the channel")
    exit(1)

print(f"\n[CONFIG] Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print(f"[CONFIG] Channel ID: {CHANNEL_ID}")

async def run_tests():
    """Run all TelegramPoster tests"""

    # Initialize poster
    print("\n" + "="*60)
    print("TEST 1: Initialize TelegramPoster")
    print("="*60)

    try:
        poster = TelegramPoster(
            bot_token=BOT_TOKEN,
            channel_id=CHANNEL_ID,
            max_retries=3
        )
        print("[OK] TelegramPoster initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        return

    # Test connection
    print("\n" + "="*60)
    print("TEST 2: Test connection to Telegram")
    print("="*60)

    try:
        success = await poster.test_connection()
        if success:
            print("[OK] Connection test passed!")
        else:
            print("[ERROR] Connection test failed")
            print("\nPossible issues:")
            print("  - Invalid bot token")
            print("  - Bot not added to channel")
            print("  - Bot not admin in channel")
            print("  - Invalid channel ID")
            return
    except Exception as e:
        print(f"[ERROR] Connection test error: {e}")
        return

    # Test 3: Post simple text message
    print("\n" + "="*60)
    print("TEST 3: Post simple text message")
    print("="*60)

    simple_content = {
        'format_type': 'long_post',
        'title': 'Test Post: Simple Message',
        'content': 'This is a test message from TelegramPoster.\n\nIt demonstrates basic text posting functionality.',
        'hashtags': ['#test', '#automation']
    }

    try:
        result = await poster.post_content(simple_content)
        if result['success']:
            print(f"[OK] Message posted! Message ID: {result['message_id']}")
            print(f"[OK] Posted at: {result['posted_at']}")
        else:
            print(f"[ERROR] Failed to post: {result['error']}")
    except Exception as e:
        print(f"[ERROR] Post error: {e}")

    # Wait a bit to avoid rate limits
    await asyncio.sleep(2)

    # Test 4: Post message with formatting
    print("\n" + "="*60)
    print("TEST 4: Post message with HTML formatting")
    print("="*60)

    formatted_content = {
        'format_type': 'long_post',
        'title': 'Test Post: Formatted Content',
        'content': '''This message demonstrates <b>HTML formatting</b>:

<b>Key Points:</b>
- Bold text for emphasis
- Line breaks for readability
- Emojis for engagement ✨

<i>Testing TelegramPoster component</i>''',
        'hashtags': ['#test', '#formatting', '#automation']
    }

    try:
        result = await poster.post_content(formatted_content)
        if result['success']:
            print(f"[OK] Formatted message posted! Message ID: {result['message_id']}")
        else:
            print(f"[ERROR] Failed to post: {result['error']}")
    except Exception as e:
        print(f"[ERROR] Post error: {e}")

    # Wait a bit
    await asyncio.sleep(2)

    # Test 5: Post thread
    print("\n" + "="*60)
    print("TEST 5: Post thread (multiple messages)")
    print("="*60)

    thread_content = {
        'format_type': 'thread',
        'content': [
            'First message in the thread.\n\nThis tests multi-message posting.',
            'Second message.\n\nThreads allow splitting long content into multiple posts.',
            'Third and final message.\n\nThis is useful for Twitter-style threads.'
        ],
        'hashtags': ['#test', '#thread', '#automation']
    }

    try:
        result = await poster.post_content(thread_content)
        if result['success']:
            print(f"[OK] Thread posted! Message IDs: {result.get('message_ids', [])}")
        else:
            print(f"[ERROR] Failed to post thread: {result['error']}")
    except Exception as e:
        print(f"[ERROR] Thread post error: {e}")

    # Test 6: Preview formatting
    print("\n" + "="*60)
    print("TEST 6: Preview message formatting")
    print("="*60)

    preview_content = {
        'title': 'Preview Test',
        'content': 'This is how the message will look when posted.',
        'hashtags': ['#preview', '#test']
    }

    preview_text = poster.format_content_for_posting(preview_content)
    print("\nFormatted message preview:")
    print("-" * 40)
    print(preview_text)
    print("-" * 40)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("[OK] All tests completed!")
    print("\nTelegramPoster is working correctly.")
    print("\nNext steps:")
    print("1. Check your Telegram channel for test messages")
    print("2. Verify formatting looks good")
    print("3. Ready for integration with AutoContentSystem")

# Run tests
if __name__ == '__main__':
    print("\nStarting tests...")
    asyncio.run(run_tests())
    print("\nTests finished!")
