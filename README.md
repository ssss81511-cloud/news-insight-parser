# News Insight Parser

AI-powered news parser and analyzer for tech insights from multiple sources.

## Features
- Multi-source parsing (HN, Reddit, Product Hunt, Dev.to, VC Blogs, TechCrunch)
- AI analysis with Groq (summarization, categorization, sentiment)
- Trend detection and clustering
- Full-text search
- Automated scheduling

## Deployment on Render.com

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. Deploy on Render
1. Go to https://render.com
2. Sign up / Log in
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Name**: news-insight-parser
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app_v2:app`

### 3. Set Environment Variables
In Render dashboard, add:
- `GROQ_API_KEY`: Your Groq API key

### 4. Deploy!
Click "Create Web Service" and wait for deployment.

## Environment Variables
- `GROQ_API_KEY` - Groq API key for AI analysis

## Local Development
```bash
pip install -r requirements.txt
python app_v2.py
```

Visit http://localhost:5001
