# 🚀 News Insight Parser

AI-powered news aggregator and content automation system for tech insights from multiple sources.

## ✨ Features

### 📰 Multi-Source Parsing
- **Hacker News** - Ask HN, Show HN, New posts
- **Reddit** - r/startups, r/SaaS, r/entrepreneur
- **Product Hunt** - Daily product launches
- **Dev.to** - Startup, SaaS, IndieHacker tags
- **TechCrunch** - Tech news, startups, funding
- **VC Blogs** - Y Combinator, Sequoia, a16z

### 🤖 AI-Powered Analysis
- Automated summarization via Groq API
- Topic detection and clustering
- Trend analysis
- Sentiment analysis
- Importance scoring

### 📱 Content Automation
- **Automated posting** to Telegram (3x daily)
- **AI content generation** from trending topics
- **AI image generation** via Pollinations.ai (FREE!)
- Smart topic rotation (no repeats for 30 days)

### ⚡ Production-Ready
- PostgreSQL database support
- Automatic scheduling (APScheduler)
- GitHub Actions keepalive for Render Free tier
- Web dashboard for monitoring

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Groq API key (get free at https://console.groq.com)
- Optional: Telegram bot token for auto-posting

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/news-insight-parser.git
cd news-insight-parser
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

4. **Run the app**
```bash
python app_v2.py
```

5. **Open in browser**
```
http://localhost:5001
```

---

## 🌐 Deploy to Render.com

### Option 1: One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Option 2: Manual Deploy

#### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

#### 2. Enable GitHub Actions
The project includes a **keepalive workflow** that prevents Render Free tier from sleeping:

1. Go to your GitHub repository
2. Click **Actions** tab
3. Enable workflows if prompted
4. The workflow runs 3x daily at 08:55, 13:55, 19:55 UTC

> **Important:** GitHub Actions scheduled workflows only work on **public repositories** on the free plan. Make sure your repo is public or use an external ping service like UptimeRobot.

#### 3. Deploy on Render

1. Go to https://render.com
2. Create account / Log in
3. Click **New +** → **Blueprint**
4. Connect your GitHub repository
5. Render will auto-detect `render.yaml` and set up:
   - Web service (Frankfurt region)
   - PostgreSQL database (Frankfurt region)

#### 4. Set Environment Variables

In Render dashboard, navigate to **Environment** and add:

**Required:**
- `GROQ_API_KEY` - Get free at https://console.groq.com

**Optional (for auto-posting):**
- `TELEGRAM_BOT_TOKEN` - Create bot at https://t.me/BotFather
- `TELEGRAM_CHANNEL_ID` - Your channel @username

**Auto-configured:**
- `DATABASE_URL` - Automatically linked from PostgreSQL

#### 5. Deploy!

Click **Apply** and wait for deployment (~5 minutes).

Your app will be available at:
```
https://news-insight-parser.onrender.com
```

---

## ⚙️ Configuration

See [.env.example](.env.example) for all available configuration options.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *required* | Groq API key for AI features |
| `TELEGRAM_BOT_TOKEN` | *optional* | Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | *optional* | Telegram channel ID |
| `AUTO_GENERATE_ENABLED` | `true` | Enable automated posting |
| `AUTO_GENERATE_HOURS` | `9,14,20` | Post times (UTC): morning, afternoon, evening |
| `CONTENT_LANGUAGE` | `ru` | Content language (ru/en) |
| `TOPIC_EXCLUDE_DAYS` | `30` | Topic rotation period |

---

## 🤖 Automation System

### How It Works

1. **Parsing** (3x daily)
   - GitHub Actions wakes up Render at scheduled times
   - Parser collects latest posts from all sources
   - AI analyzes and scores each post

2. **Topic Selection**
   - System detects trending topics from parsed posts
   - Selects unique topic (not used in last 30 days)

3. **Content Generation**
   - Groq AI generates professional content in Russian
   - Pollinations.ai creates visual (free!)

4. **Auto-Publishing**
   - Posts to Telegram channel automatically
   - Marks topic as used for rotation

### Wake-and-Run System

The system uses GitHub Actions to keep Render Free tier alive:

```yaml
# Runs 3x daily at 08:55, 13:55, 19:55 UTC
- Wakes up server (prevents 15-min sleep)
- Checks for missed tasks
- Triggers parsing if overdue (>6 hours)
- Triggers posting if missed scheduled time
```

See [.github/workflows/keepalive.yml](.github/workflows/keepalive.yml)

---

## 📊 Tech Stack

- **Backend:** Flask + Gunicorn
- **Database:** PostgreSQL (SQLite for local dev)
- **AI:** Groq API (llama-3.1-70b)
- **Image Generation:** Pollinations.ai (free!)
- **Scheduler:** APScheduler
- **Deployment:** Render.com
- **Keepalive:** GitHub Actions

---

## 🛠️ Development

### Project Structure

```
news-insight-parser/
├── app_v2.py              # Main Flask application
├── parsers/               # Source-specific parsers
│   ├── orchestrator.py   # Parser coordination
│   └── sources_config.py # Parsing schedules
├── automation/            # Content automation
│   ├── auto_content_system.py
│   ├── topic_selector.py
│   ├── telegram_poster.py
│   └── reel_generator.py
├── analyzers/             # AI analysis
│   ├── ai_analyzer.py
│   ├── content_generator.py
│   └── insights_analyzer.py
├── storage/               # Database models
│   ├── universal_models.py
│   └── universal_database.py
└── utils/                 # Utilities
    └── scheduler.py       # APScheduler config
```

### Running Tests

```bash
# Test content generation
python test_auto_content_system.py

# Test Telegram posting
python test_telegram_poster.py

# Test full workflow
python test_full_system.py
```

---

## 🔒 Security

- ✅ All secrets stored in environment variables
- ✅ `.env` files ignored by git
- ✅ No hardcoded API keys
- ✅ `.gitignore` protects sensitive data

**Before making repo public, ensure:**
1. No `.env` files committed
2. No API keys in code
3. Check `git log` for leaked secrets

---

## 📝 License

MIT License - feel free to use for your own projects!

---

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

## 📧 Support

For issues and questions, please use [GitHub Issues](https://github.com/YOUR_USERNAME/news-insight-parser/issues).

---

**Made with ❤️ using Claude Code**
