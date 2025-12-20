"""
Telegram Poster for Automation

Posts generated content to Telegram channels with proper formatting,
error handling, and retry logic.
"""
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import json
from telegram import Bot
from telegram.error import TelegramError, NetworkError, RetryAfter
from telegram.constants import ParseMode
import time


class TelegramPoster:
    """
    Posts content to Telegram channels

    Features:
    - Async posting with proper error handling
    - Automatic retry logic with exponential backoff
    - Rate limiting compliance
    - Message formatting (Markdown/HTML)
    - Media support (images)
    - Thread safety
    """

    def __init__(self, bot_token: str, channel_id: str, max_retries: int = 3):
        """
        Initialize TelegramPoster

        Args:
            bot_token: Telegram Bot API token from @BotFather
            channel_id: Channel ID (format: @channelname or -100xxxxxxxxxx)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        if not bot_token:
            raise ValueError("bot_token is required")
        if not channel_id:
            raise ValueError("channel_id is required")

        self.bot = Bot(token=bot_token)
        self.channel_id = channel_id
        self.max_retries = max_retries

        print(f"[TELEGRAM POSTER] Initialized with channel: {channel_id}", flush=True)

    async def post_content(self, content: Dict, media_path: Optional[str] = None) -> Dict:
        """
        Post generated content to Telegram channel

        Args:
            content: Generated content dictionary with structure:
                {
                    'title': str (optional),
                    'content': str or List[str] (for threads),
                    'hashtags': List[str] (optional),
                    'format_type': str ('long_post', 'reel', 'thread')
                }
            media_path: Optional path to image/video file

        Returns:
            Dict with posting result:
                {
                    'success': bool,
                    'message_id': int or None,
                    'error': str or None,
                    'posted_at': datetime
                }
        """
        print(f"[TELEGRAM POSTER] Starting post: format={content.get('format_type', 'unknown')}", flush=True)

        try:
            # Format message based on content type
            if content.get('format_type') == 'thread':
                # Thread: multiple messages
                return await self._post_thread(content, media_path)
            else:
                # Single message (long_post or reel)
                return await self._post_single_message(content, media_path)

        except Exception as e:
            print(f"[TELEGRAM POSTER] Error posting content: {e}", flush=True)
            return {
                'success': False,
                'message_id': None,
                'error': str(e),
                'posted_at': datetime.utcnow()
            }

    async def _post_single_message(self, content: Dict, media_path: Optional[str] = None) -> Dict:
        """
        Post a single message to Telegram

        Args:
            content: Content dictionary
            media_path: Optional media file

        Returns:
            Result dictionary
        """
        # Build message text
        message_text = self._format_message(content)

        # Telegram message length limit is 4096 characters
        if len(message_text) > 4000:
            print(f"[TELEGRAM POSTER] Message too long ({len(message_text)} chars), truncating...", flush=True)
            message_text = message_text[:3900] + "\n\n... (полный текст слишком длинный)"

        # Post with retries
        for attempt in range(self.max_retries):
            try:
                if media_path:
                    # Post with photo
                    with open(media_path, 'rb') as photo:
                        message = await self.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=photo,
                            caption=message_text,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    # Post text only
                    message = await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False
                    )

                print(f"[TELEGRAM POSTER] Successfully posted! Message ID: {message.message_id}", flush=True)
                return {
                    'success': True,
                    'message_id': message.message_id,
                    'error': None,
                    'posted_at': datetime.utcnow()
                }

            except RetryAfter as e:
                # Rate limited - wait and retry
                wait_time = e.retry_after + 1
                print(f"[TELEGRAM POSTER] Rate limited. Waiting {wait_time}s...", flush=True)
                await asyncio.sleep(wait_time)

            except NetworkError as e:
                # Network error - retry with exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[TELEGRAM POSTER] Network error on attempt {attempt + 1}. Retrying in {wait_time}s...", flush=True)
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except TelegramError as e:
                # Other Telegram error - don't retry
                print(f"[TELEGRAM POSTER] Telegram error: {e}", flush=True)
                raise

        # All retries exhausted
        raise Exception(f"Failed to post after {self.max_retries} attempts")

    async def _post_thread(self, content: Dict, media_path: Optional[str] = None) -> Dict:
        """
        Post a thread (multiple messages) to Telegram

        Args:
            content: Content dictionary with 'content' as List[str]
            media_path: Optional media for first message

        Returns:
            Result dictionary
        """
        thread_content = content.get('content', [])
        if isinstance(thread_content, str):
            # Not actually a thread, post as single message
            return await self._post_single_message(content, media_path)

        if not thread_content or len(thread_content) == 0:
            raise ValueError("Thread content is empty")

        print(f"[TELEGRAM POSTER] Posting thread with {len(thread_content)} messages", flush=True)

        message_ids = []
        errors = []

        # Post each message in the thread
        for i, tweet_text in enumerate(thread_content, 1):
            try:
                # Add thread numbering
                formatted_text = f"<b>{i}/{len(thread_content)}</b>\n\n{tweet_text}"

                # Add hashtags to last message
                if i == len(thread_content) and content.get('hashtags'):
                    hashtags = content['hashtags']
                    if isinstance(hashtags, str):
                        hashtags = json.loads(hashtags)
                    formatted_text += f"\n\n{' '.join(hashtags)}"

                # Post with photo only on first message
                if i == 1 and media_path:
                    with open(media_path, 'rb') as photo:
                        message = await self.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=photo,
                            caption=formatted_text,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    message = await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=formatted_text,
                        parse_mode=ParseMode.HTML
                    )

                message_ids.append(message.message_id)

                # Small delay between messages to avoid rate limits
                if i < len(thread_content):
                    await asyncio.sleep(1)

            except Exception as e:
                error_msg = f"Error posting message {i}: {str(e)}"
                print(f"[TELEGRAM POSTER] {error_msg}", flush=True)
                errors.append(error_msg)

        if message_ids:
            print(f"[TELEGRAM POSTER] Thread posted successfully! {len(message_ids)} messages", flush=True)
            return {
                'success': True,
                'message_id': message_ids[0],  # First message ID
                'message_ids': message_ids,
                'error': None if not errors else '; '.join(errors),
                'posted_at': datetime.utcnow()
            }
        else:
            raise Exception(f"Failed to post thread: {'; '.join(errors)}")

    def _format_message(self, content: Dict) -> str:
        """
        Format content for Telegram posting

        Uses HTML formatting for better presentation.

        Args:
            content: Content dictionary

        Returns:
            Formatted message text
        """
        parts = []

        # Title
        title = content.get('title', '')
        if title:
            parts.append(f"<b>{title}</b>")
            parts.append("")  # Empty line

        # Main content
        main_content = content.get('content', '')
        if isinstance(main_content, list):
            # Thread - combine all tweets
            main_content = '\n\n'.join(main_content)

        if main_content:
            # Replace markdown bold with HTML
            main_content = main_content.replace('**', '<b>').replace('**', '</b>')
            parts.append(main_content)

        # Hashtags
        hashtags = content.get('hashtags', [])
        if hashtags:
            if isinstance(hashtags, str):
                try:
                    hashtags = json.loads(hashtags)
                except:
                    hashtags = hashtags.split()

            if hashtags:
                parts.append("")  # Empty line
                parts.append(' '.join(hashtags))

        return '\n'.join(parts)

    async def test_connection(self) -> bool:
        """
        Test connection to Telegram and verify bot has access to channel

        Returns:
            True if connection successful and bot can access channel
        """
        try:
            print(f"[TELEGRAM POSTER] Testing connection...", flush=True)

            # Get bot info
            bot_info = await self.bot.get_me()
            print(f"[TELEGRAM POSTER] Bot: @{bot_info.username} ({bot_info.first_name})", flush=True)

            # Try to get chat info
            try:
                chat = await self.bot.get_chat(self.channel_id)
                print(f"[TELEGRAM POSTER] Channel: {chat.title or chat.username}", flush=True)
                print(f"[TELEGRAM POSTER] Type: {chat.type}", flush=True)
            except Exception as e:
                print(f"[TELEGRAM POSTER] Warning: Could not get chat info: {e}", flush=True)
                print(f"[TELEGRAM POSTER] This is normal if bot is not admin yet", flush=True)

            # Send test message
            test_message = await self.bot.send_message(
                chat_id=self.channel_id,
                text="<b>🤖 Test Message</b>\n\nTelegramPoster connection successful!",
                parse_mode=ParseMode.HTML
            )

            print(f"[TELEGRAM POSTER] Test message sent! Message ID: {test_message.message_id}", flush=True)
            print(f"[TELEGRAM POSTER] Connection test successful!", flush=True)

            return True

        except Exception as e:
            print(f"[TELEGRAM POSTER] Connection test failed: {e}", flush=True)
            return False

    def format_content_for_posting(self, content: Dict) -> str:
        """
        Helper method to preview how content will look when posted

        Args:
            content: Content dictionary

        Returns:
            Formatted message text
        """
        return self._format_message(content)


def sync_post(bot_token: str, channel_id: str, content: Dict, media_path: Optional[str] = None) -> Dict:
    """
    Synchronous wrapper for posting to Telegram

    Use this when you can't use async/await (e.g., in Flask routes)

    Args:
        bot_token: Telegram bot token
        channel_id: Telegram channel ID
        content: Content to post
        media_path: Optional media file

    Returns:
        Result dictionary
    """
    poster = TelegramPoster(bot_token, channel_id)

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(poster.post_content(content, media_path))
        return result
    finally:
        loop.close()
