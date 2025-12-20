# Deployment Guide - Automated Content System

Complete guide for deploying the News Insight Parser with full automation to Render.

## Prerequisites

1. GitHub repository with your code
2. Render account (https://render.com)
3. PostgreSQL database on Render
4. Telegram bot credentials (optional but recommended)
5. Groq API key

## Step 1: Prepare Environment Variables

Set these in Render Dashboard → Environment tab:

### Required Variables

```bash
# Database (auto-set by Render when you add PostgreSQL)
DATABASE_URL=postgresql://user:password@host/database

# AI Content Generation (REQUIRED)
GROQ_API_KEY=your_groq_api_key_here
```

### Optional - Telegram Posting

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=@your_channel_name

# Or for private channels:
TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx
```

### Optional - Automation Configuration

```bash
# Enable/Disable Automation
AUTO_GENERATE_ENABLED=true              # Set to 'true' to enable scheduled generation
AUTO_GENERATE_HOUR=9                    # Hour to run (0-23, default: 9 = 9 AM)
AUTO_GENERATE_MINUTE=0                  # Minute to run (0-59, default: 0)

# Topic Selection
TOPIC_EXCLUDE_DAYS=30                   # Don't repeat topics from last N days
TOPIC_PREFER_TRENDING=true              # Prefer trending topics
TOPIC_MIN_POSTS=3                       # Minimum posts required for a topic

# Content Generation
CONTENT_FORMAT=long_post                # 'long_post', 'reel', or 'thread'
CONTENT_LANGUAGE=ru                     # 'ru' or 'en'
CONTENT_TONE=professional               # 'professional', 'casual', or 'inspirational'

# Reel Generation
REEL_ASPECT_RATIO=reel                  # 'square', 'reel', 'story', 'landscape', 'twitter'
REEL_STYLE=modern                       # 'modern', 'professional', 'vibrant', 'minimal', 'dark'
ENABLE_REEL=true                        # Generate images for posts
```

## Step 2: Deploy to Render

### Option A: Deploy via Dashboard

1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: news-insight-parser
   - **Region**: Choose closest to your audience
   - **Branch**: main
   - **Root Directory**: (leave empty)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 2 --threads 4 --worker-class gthread app_v2:app`
5. Add Environment Variables (see Step 1)
6. Click "Create Web Service"

### Option B: Deploy via render.yaml

Create `render.yaml` in project root:

```yaml
services:
  - type: web
    name: news-insight-parser
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 2 --threads 4 --worker-class gthread app_v2:app
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_CHANNEL_ID
        sync: false
      - key: AUTO_GENERATE_ENABLED
        value: true
      - key: AUTO_GENERATE_HOUR
        value: 9
      - key: CONTENT_LANGUAGE
        value: ru
      - key: DATABASE_URL
        fromDatabase:
          name: news-insight-db
          property: connectionString

databases:
  - name: news-insight-db
    databaseName: news_insight
    user: news_insight_user
    plan: starter  # or 'free' for development
```

Then:
1. Push `render.yaml` to GitHub
2. In Render Dashboard: "New +" → "Blueprint"
3. Connect repository
4. Render will auto-detect render.yaml and deploy

## Step 3: Run Database Migration

After first deployment:

1. Go to Render Dashboard → your service → Shell
2. Run migration:
```bash
python migrate_add_used_topics.py
```

This creates the `used_topics` table.

## Step 4: Initial Setup

### 4.1 Run Parsers

Collect initial data:

1. Open your app: `https://your-app.onrender.com`
2. Click "Parse Now" or use API:
```bash
curl -X POST https://your-app.onrender.com/api/parse
```

3. Wait for parsing to complete (check logs)

### 4.2 Run Analytics

Generate topics from collected posts:

```bash
curl -X POST https://your-app.onrender.com/api/run-insights
```

### 4.3 Test Manual Generation

Test the automation system manually:

```bash
curl -X POST https://your-app.onrender.com/api/auto-generate
```

Expected response:
```json
{
  "status": "success",
  "content_id": 1,
  "message_id": 123,
  "topic": {
    "keywords": ["AI", "machine learning"],
    "post_count": 5
  }
}
```

If successful, check your Telegram channel for the post!

## Step 5: Enable Automation

### Option A: Via Environment Variable (Recommended)

Set in Render Dashboard:
```bash
AUTO_GENERATE_ENABLED=true
AUTO_GENERATE_HOUR=9  # 9 AM
```

Redeploy the service. Check logs for:
```
[AUTOMATION] Auto-generate: ON | Schedule: Daily at 09:00
```

### Option B: Via API

Enable after deployment:
```bash
curl -X POST https://your-app.onrender.com/api/automation/enable
```

Check status:
```bash
curl https://your-app.onrender.com/api/automation-status
```

## Step 6: Monitor

### Check Logs

In Render Dashboard → Logs, look for:

```
2025-01-15 09:00:00 [INFO] ============================================================
2025-01-15 09:00:00 [INFO] SCHEDULED CONTENT GENERATION STARTED
2025-01-15 09:00:00 [INFO] ============================================================
2025-01-15 09:00:05 [INFO] [STEP 1/7] Selecting unique topic...
2025-01-15 09:00:05 [INFO] [OK] Selected topic: ['AI', 'automation', 'LLM']
...
2025-01-15 09:01:30 [INFO] SUCCESS - Content ID: 42, Message ID: 567
2025-01-15 09:01:30 [INFO] ============================================================
```

### API Endpoints for Monitoring

```bash
# Get automation status
curl https://your-app.onrender.com/api/automation-status

# Get automation statistics
curl https://your-app.onrender.com/api/auto-stats

# Get generated content
curl https://your-app.onrender.com/api/generated-content
```

## Troubleshooting

### Automation Not Running

**Check 1**: Environment variable set?
```bash
# In Render Dashboard, verify:
AUTO_GENERATE_ENABLED=true
```

**Check 2**: Logs show scheduler enabled?
```
[AUTOMATION] Auto-generate: ON | Schedule: Daily at 09:00
```

**Check 3**: GROQ_API_KEY configured?
```
[AUTOMATION] Configured: YES | Telegram: YES
```

### Content Not Generating

**Issue**: "No suitable topic found"
- **Solution**: Run parsers first, then run analytics to generate topics
- **Check**: Visit /analytics page, should show topics

**Issue**: "No posts found for topic"
- **Solution**: Ensure posts have AI analysis (run parsers with AI enabled)
- **Check**: Database should have posts with `ai_summary` not null

**Issue**: "Content generation failed"
- **Solution**: Check GROQ_API_KEY is valid
- **Check logs**: Look for Groq API errors

### Telegram Posting Failed

**Issue**: "Bot is not a member of the channel"
- **Solution**: Add bot as admin to channel
- **See**: TELEGRAM_SETUP.md for detailed instructions

**Issue**: "Chat not found"
- **Solution**: Verify TELEGRAM_CHANNEL_ID format
  - Public: `@channelname`
  - Private: `-100xxxxxxxxxx`

### Database Issues

**Issue**: "used_topics table does not exist"
- **Solution**: Run migration in Shell:
  ```bash
  python migrate_add_used_topics.py
  ```

**Issue**: Connection errors
- **Solution**: Verify DATABASE_URL is set correctly
- **Check**: Should be `postgresql://` not `postgres://`

## Maintenance

### Daily Operations

1. **Check logs** for scheduled runs
2. **Review Telegram channel** for posted content
3. **Monitor stats** via `/api/auto-stats`

### Weekly Tasks

1. **Review topic usage**: Ensure variety
   ```bash
   curl https://your-app.onrender.com/api/auto-stats
   ```

2. **Check content quality**: Review posts, adjust tone/style if needed

3. **Database cleanup**: Remove old posts
   ```bash
   curl -X POST https://your-app.onrender.com/api/cleanup-old-posts
   ```

### Monthly Tasks

1. **Adjust configuration**: Based on performance
2. **Update topics**: Run analytics again for fresh topics
3. **Review automation stats**: Topics per week, publish rate, etc.

## Scaling

### Increase Posting Frequency

Add multiple schedules in app_v2.py:

```python
# Morning post
automation_scheduler.add_job(
    func=scheduled_content_generation,
    trigger='cron',
    hour=9,
    minute=0,
    id='morning_post'
)

# Evening post
automation_scheduler.add_job(
    func=scheduled_content_generation,
    trigger='cron',
    hour=18,
    minute=0,
    id='evening_post'
)
```

### Different Content Formats

Create multiple AutoContentSystem instances with different configs:

```python
# Long post system (morning)
auto_system_long = AutoContentSystem(..., config={'content_format': 'long_post'})

# Thread system (evening)
auto_system_thread = AutoContentSystem(..., config={'content_format': 'thread'})
```

## Best Practices

1. **Start with manual testing**: Test `/api/auto-generate` before enabling automation
2. **Monitor first week**: Check logs daily, adjust config as needed
3. **Gradual rollout**: Start with once-daily, increase if working well
4. **Quality over quantity**: Better one good post than multiple poor ones
5. **Keep data fresh**: Run parsers regularly (at least daily)
6. **Topic variety**: If running out of topics, lower `TOPIC_EXCLUDE_DAYS`

## Support

If you encounter issues:

1. Check logs in Render Dashboard
2. Test individual components:
   - Parsing: `/api/parse`
   - Analytics: `/api/run-insights`
   - Manual generation: `/api/auto-generate`
3. Verify all environment variables are set
4. Review INTEGRATION_GUIDE.md for detailed examples

## Success Criteria

System is working correctly when:

- ✅ Logs show daily scheduled execution
- ✅ Content appears in database (`generated_content` table)
- ✅ Posts appear in Telegram channel
- ✅ Topics are marked as used (no repetition)
- ✅ Images are generated (if enabled)
- ✅ Stats show increasing publish rate

## Next Steps

After successful deployment:

1. ✅ System is running automatically
2. 🔄 Monitor and adjust configuration
3. 📊 Review analytics weekly
4. 🎨 Experiment with different styles/formats
5. 📈 Scale up frequency if desired
