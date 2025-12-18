# News Insight Agent

## Purpose
Agent for parsing news sources and identifying insights, patterns, and emerging signals in the SaaS/startup ecosystem.

---

## Data Sources

Analyze content ONLY from:

1. **Indie Hackers** – discussions and comments
2. **Hacker News** – "new" and "ask" sections
3. **Product Hunt** – new launches and comments
4. **Reddit** – 2–3 SaaS-related subreddits
5. **VC blogs** – 1–2 venture funds (strategic thinking, not PR)

---

## Signals to Extract

### 1. Repeating Pains
- Founders complaining about the same problem across sources
- Operational, growth, pricing, infra, or customer-related pain
- Track frequency and context

### 2. Unusual or Emerging Language
- New terms, metaphors, or phrases
- Shifts in wording (e.g. "freemium" → "usage-based")
- Language evolution patterns

### 3. New Solution Patterns
- Similar workarounds appearing independently
- Multiple founders building near-identical tools
- Convergent problem-solving approaches

### 4. Behavioral Patterns
- Use sequential thinking
- Track decision-making patterns
- Identify behavioral shifts in founder/user actions

---

## Analysis Methodology

1. **Collection Phase**
   - Scrape/parse designated sources
   - Normalize data format
   - Timestamp and tag by source

2. **Pattern Detection**
   - Cross-reference similar complaints/solutions
   - Identify frequency thresholds
   - Map language evolution

3. **Insight Generation**
   - Cluster related signals
   - Rank by strength/frequency
   - Generate actionable insights

4. **Output Format**
   - Structured reports
   - Trend visualizations
   - Alert on emerging patterns

---

## Implementation Notes

- Respect rate limits and ToS for each source
- Implement caching to avoid redundant requests
- Use NLP for pattern matching and clustering
- Store results in structured format (JSON/DB)

---

## Deployment Guide

### 🚀 Deploying to Render.com

#### Prerequisites
1. GitHub account and repository
2. Render.com account (free tier available)
3. Groq API key for AI analysis

#### Deployment Steps

1. **Prepare Repository**
   ```bash
   # Initialize git if not already done
   git init
   git add .
   git commit -m "Initial commit"

   # Create GitHub repository and push
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Create Render Service**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect GitHub repository
   - Configure:
     - **Name**: news-insight-parser
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app_v2:app`

3. **Set Environment Variables**
   In Render dashboard, add:
   - `GROQ_API_KEY`: Your Groq API key
   - `PYTHON_VERSION`: 3.11 (optional, in render.yaml)

4. **Deploy**
   - Click "Create Web Service"
   - Wait 3-5 minutes for deployment
   - Service will be available at: `https://YOUR-APP-NAME.onrender.com`

#### Post-Deployment Setup

1. **Check Deployment Logs**
   - Go to Logs tab in Render Dashboard
   - Verify you see:
     ```
     ==================================================
     News Insight Parser - Version 2.0
     ==================================================
     Registered sources: hackernews, reddit, producthunt, devto, techcrunch, vcblogs
     [SCHEDULER] Auto-parse: OFF
     ```

2. **First Time Setup**
   - Open your deployed URL
   - Click "Запустить парсинг" (Start Parsing)
   - Wait 2-3 minutes for initial data collection
   - Run AI analysis: "🤖 AI Анализ постов"

3. **Enable Auto-Parsing** (Optional)
   - On main dashboard, click "Включить всё" (Enable All)
   - Parser will run automatically every hour
   - Sources can be enabled/disabled individually

4. **Prevent Free Tier Sleep** (Recommended)
   - Sign up at https://uptimerobot.com (free)
   - Create HTTP(S) monitor
   - URL: Your Render app URL
   - Interval: 5 minutes
   - This keeps your app awake on Render's free tier

---

## Troubleshooting

### ❌ Problem: Only Hacker News parser appears, no other sources

**Cause**: Gunicorn doesn't execute code inside `if __name__ == '__main__':` block

**Solution**: Initialization moved to module-level `init_app()` function (fixed in commit 76d36ac)

**Verification**:
```bash
# Check logs for this line:
Registered sources: hackernews, reddit, producthunt, devto, techcrunch, vcblogs

# If you only see 'hackernews', redeploy with latest code
```

---

### ❌ Problem: Scheduler not starting on deployment

**Cause**: `scheduler.start()` was inside `if __name__ == '__main__':` block

**Solution**: Moved to `init_app()` which runs on module import (fixed in commit 76d36ac)

**Verification**:
```python
# Check /api/scheduler/status endpoint
# Should show: "running": true
```

---

### ❌ Problem: No logs visible in Render after "Your service is live"

**Cause**: Gunicorn buffers stdout by default

**Solution**: Added `flush=True` to all print statements (fixed in commit 76d36ac)

**Alternative**: Use Python's logging module or loguru

---

### ❌ Problem: Empty database after deployment

**Cause**: New deployment = fresh database (SQLite doesn't persist on Render free tier)

**Solutions**:
1. **Short-term**: Run manual parsing after each deployment
2. **Long-term**: Migrate to PostgreSQL (Render provides free PostgreSQL)
   - Update `UniversalDatabaseManager` connection string
   - Database will persist across deployments

---

### ❌ Problem: Authentication errors when pushing to GitHub

**Symptoms**:
```
remote: Write access to repository not granted
fatal: The requested URL returned error: 403
```

**Solution**:
1. Create GitHub Personal Access Token:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scopes: `repo`, `workflow`
   - Copy token immediately (shown only once)

2. Push with token:
   ```bash
   git push https://YOUR_TOKEN@github.com/USERNAME/REPO.git main
   ```

---

### ⚠️ Problem: Render free tier sleeps after 15 minutes

**Expected Behavior**: Free tier services sleep after 15 minutes of inactivity

**Solution**: Set up UptimeRobot monitoring (see Post-Deployment Setup)

**Note**: First request after sleep takes 30-60 seconds (cold start)

---

## Architecture Notes

### Key Files
- `app_v2.py` - Main Flask application (Universal architecture)
- `parsers/orchestrator.py` - Multi-parser coordination
- `storage/universal_database.py` - Unified data storage
- `analyzers/ai_analyzer.py` - Groq AI integration
- `render.yaml` - Render.com deployment config

### Gunicorn Compatibility
**Critical**: All initialization must happen at module level, not in `if __name__ == '__main__':` block

```python
# ❌ Wrong (doesn't work with gunicorn)
if __name__ == '__main__':
    scheduler.start()
    app.run()

# ✅ Correct (works with gunicorn)
def init_app():
    scheduler.start()

init_app()  # Runs on module import

if __name__ == '__main__':
    app.run()  # Only for local development
```

---

## Monitoring & Maintenance

### Daily Checks
- [ ] Check /api/status for errors
- [ ] Verify scheduler is running
- [ ] Review detected signals in /signals

### Weekly Maintenance
- [ ] Clean up old posts (>60 days): "Очистить старые посты"
- [ ] Review trending signals
- [ ] Update API keys if needed

### Monthly
- [ ] Check Render usage/limits
- [ ] Review AI analysis quality
- [ ] Update parsers if source APIs changed

---

## Future Improvements

1. **Database Persistence**
   - [ ] Migrate SQLite → PostgreSQL
   - [ ] Set up automated backups

2. **Monitoring**
   - [ ] Add error tracking (Sentry)
   - [ ] Set up alerts for parser failures
   - [ ] Dashboard for parser health

3. **Performance**
   - [ ] Implement Redis caching
   - [ ] Optimize database queries
   - [ ] Add CDN for static assets

4. **Features**
   - [ ] Export signals to CSV/JSON
   - [ ] Webhook notifications for critical signals
   - [ ] API endpoints for external integrations
