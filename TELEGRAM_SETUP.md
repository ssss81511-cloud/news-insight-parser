# Telegram Bot Setup Guide

This guide shows you how to set up a Telegram bot for automated posting.

## Step 1: Create a Telegram Bot

1. Open Telegram app (mobile or desktop)
2. Search for **@BotFather** (official Telegram bot for creating bots)
3. Start a chat with @BotFather
4. Send the command: `/newbot`
5. BotFather will ask you for a name for your bot
   - Enter a display name (e.g., "News Insight Bot")
6. BotFather will ask for a username for your bot
   - Must end with "bot" (e.g., "news_insight_bot")
   - Must be unique
7. BotFather will send you a message with your **bot token**
   - It looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **IMPORTANT:** Keep this token secret! Anyone with this token can control your bot

Example conversation with BotFather:
```
You: /newbot
BotFather: Alright, a new bot. How are we going to call it? Please choose a name for your bot.

You: News Insight Bot
BotFather: Good. Now let's choose a username for your bot. It must end in `bot`.

You: news_insight_bot
BotFather: Done! Congratulations on your new bot. You will find it at t.me/news_insight_bot.
You can now add a description, about section and profile picture for your bot, see /help for a list of commands.

Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

For a description of the Bot API, see this page: https://core.telegram.org/bots/api
```

## Step 2: Create a Telegram Channel

You need a channel where the bot will post content.

### Option A: Create a New Public Channel

1. In Telegram, click the menu (☰) and select "New Channel"
2. Enter channel name (e.g., "Tech Insights")
3. Enter description (optional)
4. Choose "Public Channel"
5. Set a username for your channel (e.g., `tech_insights_news`)
   - Your channel will be accessible at `t.me/tech_insights_news`
6. Click "Create"

### Option B: Use Existing Channel

- You must be the owner/admin of the channel
- The channel can be public or private

## Step 3: Add Bot as Admin to Channel

1. Open your channel
2. Click on channel name at the top
3. Click "Administrators" or "Edit"
4. Click "Add Admin"
5. Search for your bot username (e.g., `@news_insight_bot`)
6. Select your bot
7. Give it permission to "Post Messages"
   - Optional: Also enable "Edit Messages of Others" if you want to update posts
8. Click "Save" or "Done"

## Step 4: Get Channel ID

For **Public Channels:**
- The channel ID is just `@channelname`
- Example: `@tech_insights_news`

For **Private Channels:**
- You need the numeric ID (format: `-100xxxxxxxxxx`)
- To get it:
  1. Forward any message from the channel to @userinfobot
  2. The bot will reply with the channel ID
  3. Or use this method:
     - Add your bot to the channel as admin
     - Send a test message to the channel
     - Use Telegram API to get updates: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
     - Look for "chat":{"id":-100xxxxxxxxxx}

## Step 5: Set Environment Variables

Add these to your `.env` file or Render environment variables:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=@tech_insights_news
```

For Render deployment:
1. Go to your Render dashboard
2. Select your web service
3. Go to "Environment" tab
4. Add environment variables:
   - Key: `TELEGRAM_BOT_TOKEN`, Value: `your_bot_token`
   - Key: `TELEGRAM_CHANNEL_ID`, Value: `@your_channel`
5. Click "Save Changes"

## Step 6: Test the Setup

Run the test script to verify everything works:

```bash
export TELEGRAM_BOT_TOKEN='your_bot_token'
export TELEGRAM_CHANNEL_ID='@your_channel'
python test_telegram_poster.py
```

The test will:
1. Connect to Telegram API
2. Verify bot can access the channel
3. Send test messages
4. Test formatting and threads

Expected output:
```
============================================================
TELEGRAM POSTER TEST
============================================================

[CONFIG] Bot Token: 1234567890...xyz
[CONFIG] Channel ID: @tech_insights_news

============================================================
TEST 1: Initialize TelegramPoster
============================================================
[OK] TelegramPoster initialized

============================================================
TEST 2: Test connection to Telegram
============================================================
[TELEGRAM POSTER] Testing connection...
[TELEGRAM POSTER] Bot: @news_insight_bot (News Insight Bot)
[TELEGRAM POSTER] Channel: Tech Insights
[TELEGRAM POSTER] Test message sent! Message ID: 123
[OK] Connection test passed!

...
```

## Troubleshooting

### Error: "Unauthorized"
- **Problem:** Invalid bot token
- **Solution:** Double-check the token from @BotFather, make sure there are no extra spaces

### Error: "Chat not found"
- **Problem:** Invalid channel ID
- **Solution:**
  - For public channels: Make sure to include @ symbol
  - Verify the channel username is correct
  - For private channels: Get the numeric ID (-100xxxxxxxxxx)

### Error: "Bot is not a member of the channel"
- **Problem:** Bot not added to channel
- **Solution:** Add bot as admin to the channel (see Step 3)

### Error: "Bot was kicked from the channel"
- **Problem:** Bot was removed from channel
- **Solution:** Re-add bot as admin

### Error: "Not enough rights to send messages"
- **Problem:** Bot doesn't have permission to post
- **Solution:**
  1. Open channel settings
  2. Go to Administrators
  3. Find your bot
  4. Enable "Post Messages" permission

### Messages not appearing in channel
- **Problem:** Posting to wrong channel or bot not admin
- **Solution:**
  1. Verify TELEGRAM_CHANNEL_ID is correct
  2. Check bot is admin with post permission
  3. Try sending a manual test message

## Security Best Practices

1. **Never commit bot token to git**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Regenerate token if leaked**
   - Go to @BotFather
   - Send `/mybots`
   - Select your bot
   - Choose "API Token" → "Revoke current token"
   - Get new token and update environment variables

3. **Limit bot permissions**
   - Only give necessary permissions
   - "Post Messages" is usually enough for automation

4. **Monitor bot activity**
   - Check channel regularly
   - Review posted content
   - Set up alerts for errors

## Next Steps

Once setup is complete:

1. ✓ Bot created and configured
2. ✓ Channel created and bot added as admin
3. ✓ Environment variables set
4. ✓ Test script runs successfully

Now you're ready to:
- Integrate TelegramPoster with AutoContentSystem
- Set up automated daily posting
- Generate and post content automatically

## Useful Commands

**@BotFather Commands:**
- `/mybots` - List your bots
- `/setname` - Change bot name
- `/setdescription` - Set bot description
- `/setabouttext` - Set "About" text
- `/setuserpic` - Set bot profile picture
- `/deletebot` - Delete bot
- `/revoke` - Revoke bot token (get new one)

**Test Posting Manually:**
```python
from automation.telegram_poster import TelegramPoster
import asyncio

async def test():
    poster = TelegramPoster(
        bot_token='YOUR_BOT_TOKEN',
        channel_id='@your_channel'
    )

    await poster.post_content({
        'title': 'Test Post',
        'content': 'This is a test!',
        'hashtags': ['#test']
    })

asyncio.run(test())
```

## Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [BotFather Official Guide](https://core.telegram.org/bots#6-botfather)
- [Channel Management Guide](https://telegram.org/tour/channels)

## Support

If you encounter issues:
1. Check this guide for troubleshooting steps
2. Verify environment variables are set correctly
3. Run test script with verbose logging
4. Check Telegram API status: https://www.telegram.org/
