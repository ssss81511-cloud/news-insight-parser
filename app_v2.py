"""
Flask web interface for News Insight Parser - Version 2
Uses UniversalPost and ParserOrchestrator
"""
from flask import Flask, render_template, jsonify, request
from storage.universal_database import UniversalDatabaseManager
from parsers.orchestrator import create_orchestrator
from analyzers.enhanced_signal_detector import EnhancedSignalDetector
from analyzers.insights_analyzer import InsightsAnalyzer
from analyzers.ai_analyzer import AIAnalyzer
from analyzers.content_generator import ContentGenerator
from utils.helpers import time_ago, truncate_text, clean_html
from utils.scheduler import get_scheduler
from datetime import datetime, timezone
import threading
import os
import json
import logging

# Automation imports
from automation.topic_selector import TopicSelector
from automation.telegram_poster import TelegramPoster
from automation.reel_generator import create_reel_generator
from automation.auto_content_system import AutoContentSystem, sync_generate_and_post
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Add custom Jinja2 filter for JSON parsing
@app.template_filter('fromjson')
def fromjson_filter(value):
    """Parse JSON string in templates"""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

# Initialize database with universal models
# Use PostgreSQL on production (Render) or SQLite locally
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/insights.db')
db = UniversalDatabaseManager(database_url=DATABASE_URL)

# Create orchestrator with parsers
orchestrator = create_orchestrator(db)

# Signal detector
signal_detector = EnhancedSignalDetector(db)

# Insights analyzer
insights_analyzer = InsightsAnalyzer(db)

# AI analyzer (Groq)
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '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')
ai_analyzer = AIAnalyzer(api_key=GROQ_API_KEY)

# Content generator for social media
content_generator = ContentGenerator(api_key=GROQ_API_KEY, db_manager=db)

# Scheduler for automatic parsing
scheduler = get_scheduler()

# ============================================================
# AUTOMATION SYSTEM INITIALIZATION
# ============================================================

# Environment variables for automation
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')  # For stock photo fallback - get free at https://www.pexels.com/api/
AUTO_GENERATE_ENABLED = os.getenv('AUTO_GENERATE_ENABLED', 'false').lower() == 'true'
AUTO_GENERATE_HOUR = int(os.getenv('AUTO_GENERATE_HOUR', '9'))
AUTO_GENERATE_MINUTE = int(os.getenv('AUTO_GENERATE_MINUTE', '0'))

# Configure logging for automation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize automation components
topic_selector = TopicSelector(db, insights_analyzer=insights_analyzer)

# IMPORTANT: use_ai=True enables FREE AI image generation via Pollinations.ai
# Priority: Pollinations AI (FREE!) > Pexels Stock > Gradient Fallback
print(f"[STARTUP] AI Image Generation: Pollinations.ai (FREE - no API key needed!)", flush=True)
print(f"[STARTUP] PEXELS_API_KEY (fallback): {'✅ SET' if PEXELS_API_KEY else '❌ NOT SET'}", flush=True)

reel_generator = create_reel_generator(
    output_dir='generated_reels',
    use_ai=True,  # FREE AI generation via Pollinations!
    pexels_key=PEXELS_API_KEY
)

# Initialize Telegram poster if credentials are provided
telegram_poster = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
    try:
        telegram_poster = TelegramPoster(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)
        logger.info(f"Telegram poster initialized for channel: {TELEGRAM_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram poster: {e}")

# Initialize AutoContentSystem if GROQ API key is available
auto_system = None
if GROQ_API_KEY:
    auto_system = AutoContentSystem(
        db_manager=db,
        content_generator=content_generator,
        topic_selector=topic_selector,
        telegram_poster=telegram_poster,
        reel_generator=reel_generator,
        config={
            'topic_exclude_days': int(os.getenv('TOPIC_EXCLUDE_DAYS', '30')),
            'topic_prefer_trending': os.getenv('TOPIC_PREFER_TRENDING', 'true').lower() == 'true',
            'topic_min_posts': int(os.getenv('TOPIC_MIN_POSTS', '3')),
            'content_format': os.getenv('CONTENT_FORMAT', 'long_post'),
            'content_language': os.getenv('CONTENT_LANGUAGE', 'ru'),
            'content_tone': os.getenv('CONTENT_TONE', 'professional'),
            'reel_aspect_ratio': os.getenv('REEL_ASPECT_RATIO', 'square'),
            'reel_style': os.getenv('REEL_STYLE', 'modern'),
            'enable_reel': os.getenv('ENABLE_REEL', 'true').lower() == 'true',
            'enable_telegram': telegram_poster is not None,
        }
    )
    logger.info("AutoContentSystem initialized")

# Initialize automation scheduler
automation_scheduler = BackgroundScheduler()
automation_scheduler_enabled = False

# Set up scheduler with orchestrator and analyze callback
scheduler.set_orchestrator(orchestrator)
scheduler.set_analyze_callback(
    lambda: signal_detector.detect_all_signals(lookback_days=7, min_mentions=3)
)

# Parser status
parser_status = {
    'is_running': False,
    'last_run': None,
    'current_section': None
}


@app.route('/')
def index():
    """Main dashboard page"""
    stats = db.get_stats()
    recent_runs = db.get_parser_runs(limit=5)

    return render_template('index_v2.html',
                          stats=stats,
                          recent_runs=recent_runs,
                          parser_status=parser_status,
                          time_ago=time_ago)


@app.route('/posts')
def posts():
    """View all posts"""
    post_type = request.args.get('type', None)
    source = request.args.get('source', None)
    min_importance = float(request.args.get('min_importance', 0))
    search_query = request.args.get('q', None)

    posts = db.get_recent_posts(
        limit=100,
        post_type=post_type,
        source=source,
        min_importance=min_importance,
        search_query=search_query
    )

    return render_template('posts_v2.html',
                          posts=posts,
                          post_type=post_type,
                          source=source,
                          search_query=search_query,
                          time_ago=time_ago,
                          truncate_text=truncate_text,
                          clean_html=clean_html)


@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """Detailed view of a single post"""
    post = db.get_post_by_id(post_id)

    if not post:
        return "Post not found", 404

    # Get comments
    comments = db.get_post_comments(post_id)

    # Get related posts (from same cluster)
    related_posts = db.find_duplicate_posts(post)

    return render_template('post_detail.html',
                          post=post,
                          comments=comments,
                          related_posts=related_posts,
                          time_ago=time_ago,
                          clean_html=clean_html)


@app.route('/signals')
def signals():
    """View detected signals"""
    priority = request.args.get('priority', None)
    trending_only = request.args.get('trending', 'false').lower() == 'true'

    signals = db.get_prioritized_signals(
        limit=50,
        priority=priority,
        only_trending=trending_only
    )

    # Also get cross-source signals
    cross_source_signals = db.get_cross_source_signals()

    return render_template('signals_v2.html',
                          signals=signals,
                          cross_source_signals=cross_source_signals,
                          time_ago=time_ago)


@app.route('/analytics')
def analytics():
    """Advanced analytics dashboard"""
    lookback_days = int(request.args.get('days', 7))

    # Get all analytics data
    top_posts = insights_analyzer.get_top_posts(lookback_days=lookback_days, top_n=20)
    topics = insights_analyzer.detect_topics(lookback_days=lookback_days)
    clusters = insights_analyzer.cluster_similar_posts(lookback_days=lookback_days)
    trends = insights_analyzer.detect_trends(lookback_days=lookback_days * 2)
    source_dist = insights_analyzer.get_source_distribution(lookback_days=lookback_days)

    return render_template('analytics.html',
                          top_posts=top_posts,
                          topics=topics,
                          clusters=clusters,
                          trends=trends,
                          source_dist=source_dist,
                          lookback_days=lookback_days)


@app.route('/api/parse', methods=['POST'])
def start_parsing():
    """Start parsing all sources"""
    if parser_status['is_running']:
        return jsonify({'status': 'error', 'message': 'Парсер уже запущен'}), 400

    # Get parameters
    data = request.get_json() or {}
    sources = data.get('sources', None)  # None = all sources
    limit = data.get('limit', 20)

    # Run parser in background thread
    thread = threading.Thread(target=run_parser, args=(sources, limit))
    thread.start()

    return jsonify({'status': 'success', 'message': 'Парсер запущен'})


@app.route('/api/analyze-signals', methods=['POST'])
def analyze_signals():
    """Run signal detection"""
    data = request.get_json() or {}
    lookback_days = data.get('lookback_days', 7)
    min_mentions = data.get('min_mentions', 3)

    try:
        # Run in background
        thread = threading.Thread(
            target=signal_detector.detect_all_signals,
            args=(lookback_days, min_mentions)
        )
        thread.start()

        return jsonify({
            'status': 'success',
            'message': f'Анализ сигналов запущен (последние {lookback_days} дней)'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/run-insights', methods=['POST'])
def run_insights():
    """Run insights analysis to create topics"""
    try:
        logger.info("Running insights analysis via API")

        # Run insights analysis - detect_topics returns a list of topics
        topics = insights_analyzer.detect_topics(lookback_days=30, n_topics=10, n_words=10)

        return jsonify({
            'status': 'success',
            'message': f'Insights analysis completed',
            'topics_found': len(topics) if topics else 0,
            'topics': topics
        })
    except Exception as e:
        logger.error(f"Insights analysis error: {e}")
        import traceback
        return jsonify({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/status')
def get_status():
    """Get current parser status"""
    stats = db.get_stats()
    orch_status = orchestrator.get_status()
    scheduler_status = scheduler.get_status()

    return jsonify({
        'parser_status': parser_status,
        'orchestrator_status': orch_status,
        'scheduler_status': scheduler_status,
        'stats': stats
    })


@app.route('/api/scheduler/enable', methods=['POST'])
def enable_scheduler():
    """Enable automatic parsing for all sources"""
    data = request.get_json() or {}
    source_states = data.get('sources', None)  # Optional: {source_name: enabled}

    try:
        scheduler.enable_all(source_states=source_states)

        return jsonify({
            'status': 'success',
            'message': 'Автоматический парсинг включен'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/scheduler/disable', methods=['POST'])
def disable_scheduler():
    """Disable automatic parsing"""
    try:
        scheduler.disable_all()

        return jsonify({
            'status': 'success',
            'message': 'Автоматический парсинг отключен'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/scheduler/source/<source_name>/enable', methods=['POST'])
def enable_source(source_name):
    """Enable automatic parsing for a specific source"""
    try:
        scheduler.enable_source(source_name)

        return jsonify({
            'status': 'success',
            'message': f'Источник {source_name} включен'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/scheduler/source/<source_name>/disable', methods=['POST'])
def disable_source(source_name):
    """Disable automatic parsing for a specific source"""
    try:
        scheduler.disable_source(source_name)

        return jsonify({
            'status': 'success',
            'message': f'Источник {source_name} отключен'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/scheduler/status')
def get_scheduler_status():
    """Get scheduler status"""
    return jsonify(scheduler.get_status())


@app.route('/api/cleanup-old-posts', methods=['POST'])
def cleanup_old_posts():
    """Delete posts older than 2 months"""
    try:
        deleted_count = db.cleanup_old_posts(days_old=60)
        return jsonify({
            'status': 'success',
            'message': f'Удалено {deleted_count} старых постов',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ai-analyze-post/<int:post_id>', methods=['POST'])
def ai_analyze_post(post_id):
    """AI analyze a single post"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            return jsonify({'status': 'error', 'message': 'Post not found'}), 404

        # Run AI analysis
        analysis = ai_analyzer.analyze_post(post.title, post.content or '')

        # Save results
        db.save_ai_analysis(post_id, analysis)

        return jsonify({
            'status': 'success',
            'message': 'AI анализ завершен',
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/ai-analyze-batch', methods=['POST'])
def ai_analyze_batch():
    """AI analyze top posts without AI analysis"""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 20)

        # Get posts without AI analysis
        from storage.universal_models import UniversalPost

        posts = db.session.query(UniversalPost).filter(
            UniversalPost.ai_summary == None
        ).order_by(
            UniversalPost.importance_score.desc()
        ).limit(limit).all()

        if not posts:
            return jsonify({
                'status': 'success',
                'message': 'Все посты уже проанализированы',
                'analyzed_count': 0
            })

        # Analyze in background
        def analyze_posts():
            analyzed = 0
            for post in posts:
                try:
                    analysis = ai_analyzer.analyze_post(post.title, post.content or '')
                    db.save_ai_analysis(post.id, analysis)
                    analyzed += 1
                except Exception as e:
                    print(f"Error analyzing post {post.id}: {e}")
            print(f"Batch analysis complete: {analyzed} posts analyzed")

        thread = threading.Thread(target=analyze_posts)
        thread.start()

        return jsonify({
            'status': 'success',
            'message': f'Запущен анализ {len(posts)} постов (фоновая задача)',
            'posts_to_analyze': len(posts)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/content-studio')
def content_studio():
    """Content generation studio page"""
    # Get clusters for selection
    clusters = insights_analyzer.cluster_similar_posts(lookback_days=7)

    # Get trending keywords
    trends = insights_analyzer.detect_trends(lookback_days=14)

    # Get topics
    topics = insights_analyzer.detect_topics(lookback_days=7)

    # Get recently generated content
    generated = db.get_generated_content(limit=20)

    print(f"[CONTENT STUDIO] Clusters: {len(clusters)}, Trends: {len(trends.get('trending_keywords', []))}, Topics: {len(topics)}", flush=True)
    if topics:
        print(f"[CONTENT STUDIO] First topic keywords: {topics[0].get('keywords', [])[:3]}", flush=True)

    return render_template('content_studio.html',
                          clusters=clusters,
                          trends=trends.get('trending_keywords', []),
                          topics=topics,
                          generated=generated)


@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    """Generate social media content"""
    try:
        data = request.get_json() or {}

        source_type = data.get('source_type')  # 'cluster', 'trend', 'topic', 'custom'
        format_type = data.get('format', 'long_post')  # 'long_post', 'reel', 'thread'
        tone = data.get('tone', 'professional')
        language = data.get('language', 'en')

        print(f"[CONTENT GEN] Starting: source={source_type}, format={format_type}, language={language}, tone={tone}", flush=True)

        # Generate based on source type
        if source_type == 'cluster':
            cluster_id = data.get('cluster_id')
            print(f"[CONTENT GEN] Cluster mode: Getting top 15 posts for cluster {cluster_id}", flush=True)

            from storage.universal_models import UniversalPost
            # Get top posts with AI analysis
            posts = db.session.query(UniversalPost).filter(
                UniversalPost.ai_summary != None
            ).order_by(
                UniversalPost.importance_score.desc()
            ).limit(15).all()

            print(f"[CONTENT GEN] Found {len(posts)} posts with AI analysis", flush=True)

            if not posts:
                return jsonify({'status': 'error', 'message': 'Нет постов с AI анализом. Сначала запустите парсинг.'}), 400

            result = content_generator.generate_from_cluster(
                posts, format_type, tone, language
            )
            result['source_type'] = 'cluster'
            result['source_description'] = f'Top {len(posts)} posts'

        elif source_type == 'trend':
            keyword = data.get('keyword')
            lookback_days = data.get('lookback_days', 7)
            print(f"[CONTENT GEN] Trend mode: keyword='{keyword}', lookback={lookback_days} days", flush=True)

            result = content_generator.generate_from_trend(
                keyword, lookback_days, format_type, tone, language
            )
            result['source_type'] = 'trend'
            result['source_description'] = f'Trending: {keyword}'

        elif source_type == 'topic':
            keywords = data.get('keywords', [])
            lookback_days = data.get('lookback_days', 7)

            # Validate keywords
            if not keywords or not isinstance(keywords, list):
                print(f"[CONTENT GEN] ERROR: Invalid keywords={keywords}", flush=True)
                return jsonify({'status': 'error', 'message': 'Неверный формат ключевых слов топика'}), 400

            print(f"[CONTENT GEN] Topic mode: keywords={keywords[:3]}..., total={len(keywords)}, lookback={lookback_days} days", flush=True)

            result = content_generator.generate_from_topic(
                keywords, lookback_days, format_type, tone, language
            )
            result['source_type'] = 'topic'
            result['source_description'] = f'Topic: {", ".join(keywords[:3])}'

        elif source_type == 'custom':
            # Custom post IDs
            post_ids = data.get('post_ids', [])
            print(f"[CONTENT GEN] Custom mode: {len(post_ids)} post IDs", flush=True)

            from storage.universal_models import UniversalPost

            posts = db.session.query(UniversalPost).filter(
                UniversalPost.id.in_(post_ids)
            ).all()

            if not posts:
                return jsonify({'status': 'error', 'message': 'Указанные посты не найдены'}), 400

            result = content_generator.generate_from_cluster(
                posts, format_type, tone, language
            )
            result['source_type'] = 'custom'
            result['source_description'] = f'{len(post_ids)} selected posts'
        else:
            print(f"[CONTENT GEN] ERROR: Invalid source_type={source_type}", flush=True)
            return jsonify({'status': 'error', 'message': 'Invalid source_type'}), 400

        print(f"[CONTENT GEN] Generation successful! Content length: {len(str(result.get('content', '')))} chars", flush=True)

        # Save to database
        result['language'] = language
        result['tone'] = tone
        content_id = db.save_generated_content(result)

        print(f"[CONTENT GEN] Saved to database with ID: {content_id}", flush=True)

        return jsonify({
            'status': 'success',
            'message': 'Content generated successfully',
            'content_id': content_id,
            'content': result
        })

    except Exception as e:
        import traceback
        error_msg = f"{e}\n{traceback.format_exc()}"
        print(f"[CONTENT GEN] ERROR: {error_msg}", flush=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/generated-content')
def get_generated_content_api():
    """Get generated content list"""
    format_type = request.args.get('format', None)
    only_published = request.args.get('published', 'false').lower() == 'true'

    content = db.get_generated_content(
        limit=50,
        format_type=format_type,
        only_published=only_published
    )

    # Convert to dict for JSON
    result = []
    for c in content:
        result.append({
            'id': c.id,
            'format': c.format_type,
            'title': c.title,
            'content': c.content,
            'hashtags': c.hashtags,
            'word_count': c.word_count,
            'is_published': c.is_published,
            'platform': c.platform,
            'created_at': c.created_at.isoformat() if c.created_at else None
        })

    return jsonify(result)


@app.route('/api/mark-content-published/<int:content_id>', methods=['POST'])
def mark_published(content_id):
    """Mark content as published"""
    try:
        data = request.get_json() or {}
        platform = data.get('platform', 'unknown')

        db.mark_content_published(content_id, platform)

        return jsonify({
            'status': 'success',
            'message': 'Content marked as published'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/delete-content/<int:content_id>', methods=['DELETE'])
def delete_content(content_id):
    """Delete generated content"""
    try:
        success = db.delete_generated_content(content_id)

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Content deleted'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Content not found'
            }), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# TEST DASHBOARD
# ============================================================

@app.route('/test-dashboard')
def test_dashboard():
    """Визуальный интерфейс для тестирования системы"""
    return render_template('test_dashboard.html')


@app.route('/api/posts/count')
def get_posts_count():
    """Get total count of posts in database"""
    try:
        from storage.universal_models import UniversalPost
        count = db.session.query(UniversalPost).count()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/topics')
def get_topics():
    """Get all topics from analytics"""
    try:
        # Use insights_analyzer to detect topics from recent posts
        topics = insights_analyzer.detect_topics(lookback_days=30, n_topics=10, n_words=10)
        return jsonify(topics if topics else [])
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# AUTOMATION API ENDPOINTS
# ============================================================

@app.route('/api/auto-generate', methods=['POST'])
def trigger_auto_generate():
    """Manually trigger automated content generation"""
    if not auto_system:
        return jsonify({
            'status': 'error',
            'message': 'AutoContentSystem not configured. Check GROQ_API_KEY.'
        }), 500

    logger.info("Manual auto-generate triggered via API")

    try:
        result = sync_generate_and_post(auto_system)

        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'content_id': result.get('content_id'),
            'message_id': result.get('message_id'),
            'image_path': result.get('image_path'),
            'topic': {
                'keywords': result.get('topic', {}).get('keywords', [])[:5] if result.get('topic') else None,
                'post_count': result.get('topic', {}).get('post_count', 0) if result.get('topic') else 0
            },
            'error': result.get('error'),
            'timestamp': result.get('timestamp').isoformat() if result.get('timestamp') else None
        })
    except Exception as e:
        logger.error(f"Auto-generate failed: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auto-stats', methods=['GET'])
def get_auto_stats():
    """Get automation system statistics"""
    if not auto_system:
        return jsonify({
            'status': 'error',
            'message': 'AutoContentSystem not configured'
        }), 500

    try:
        stats = auto_system.get_stats()
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Failed to get auto-stats: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/automation-status', methods=['GET'])
def get_automation_status():
    """Get automation scheduler status"""
    global automation_scheduler_enabled

    jobs = []
    if automation_scheduler and automation_scheduler_enabled:
        for job in automation_scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

    return jsonify({
        'enabled': automation_scheduler_enabled,
        'configured': auto_system is not None,
        'telegram_enabled': telegram_poster is not None,
        'schedule': f"{AUTO_GENERATE_HOUR:02d}:{AUTO_GENERATE_MINUTE:02d}" if AUTO_GENERATE_ENABLED else None,
        'jobs': jobs,
        'config': auto_system.config if auto_system else None
    })


@app.route('/api/automation/enable', methods=['POST'])
def enable_automation():
    """Enable automated content generation"""
    global automation_scheduler_enabled

    if not auto_system:
        return jsonify({
            'status': 'error',
            'message': 'AutoContentSystem not configured'
        }), 500

    try:
        # Add scheduled job if not already added
        if not automation_scheduler_enabled:
            automation_scheduler.add_job(
                func=scheduled_content_generation,
                trigger='cron',
                hour=AUTO_GENERATE_HOUR,
                minute=AUTO_GENERATE_MINUTE,
                id='daily_content_generation',
                name='Daily automated content generation',
                replace_existing=True
            )
            automation_scheduler_enabled = True
            logger.info(f"Automation enabled - Will run daily at {AUTO_GENERATE_HOUR:02d}:{AUTO_GENERATE_MINUTE:02d}")

        return jsonify({
            'status': 'success',
            'message': f'Automation enabled - Runs daily at {AUTO_GENERATE_HOUR:02d}:{AUTO_GENERATE_MINUTE:02d}'
        })
    except Exception as e:
        logger.error(f"Failed to enable automation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/automation/disable', methods=['POST'])
def disable_automation():
    """Disable automated content generation"""
    global automation_scheduler_enabled

    try:
        if automation_scheduler_enabled:
            automation_scheduler.remove_job('daily_content_generation')
            automation_scheduler_enabled = False
            logger.info("Automation disabled")

        return jsonify({
            'status': 'success',
            'message': 'Automation disabled'
        })
    except Exception as e:
        logger.error(f"Failed to disable automation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


def scheduled_content_generation():
    """
    Scheduled job for automated content generation

    This runs on a schedule (e.g., daily at 9 AM)
    """
    if not auto_system:
        logger.error("AutoContentSystem not initialized")
        return

    logger.info("="*60)
    logger.info("SCHEDULED CONTENT GENERATION STARTED")
    logger.info("="*60)

    try:
        result = sync_generate_and_post(auto_system)

        if result['success']:
            logger.info(f"SUCCESS - Content ID: {result['content_id']}, Message ID: {result['message_id']}")
            if result.get('topic'):
                logger.info(f"Topic: {result['topic'].get('keywords', [])[:3]}")
        else:
            logger.error(f"FAILED - {result['error']}")
    except Exception as e:
        logger.error(f"Scheduled generation failed: {e}", exc_info=True)

    logger.info("="*60)


def run_auto_ai_analysis():
    """
    Automatically analyze all posts without AI analysis
    Called after parsing completes
    """
    try:
        from storage.universal_models import UniversalPost

        # Get ALL posts without AI analysis (no limit!)
        posts = db.session.query(UniversalPost).filter(
            UniversalPost.ai_summary == None
        ).order_by(
            UniversalPost.importance_score.desc()
        ).all()

        if not posts:
            print("[AI] No posts to analyze", flush=True)
            return

        print(f"[AI] Found {len(posts)} posts without AI analysis", flush=True)

        analyzed = 0
        failed = 0

        for post in posts:
            try:
                print(f"[AI] Analyzing post {post.id}: {post.title[:50]}...", flush=True)
                analysis = ai_analyzer.analyze_post(post.title, post.content or '')
                db.save_ai_analysis(post.id, analysis)
                analyzed += 1
                print(f"[AI] Successfully analyzed post {post.id} ({analyzed}/{len(posts)})", flush=True)
            except Exception as e:
                failed += 1
                print(f"[AI] Failed to analyze post {post.id}: {e}", flush=True)

        print(f"[AI] AI analysis complete: {analyzed} analyzed, {failed} failed", flush=True)

    except Exception as e:
        print(f"[AI] Error in auto AI analysis: {e}", flush=True)


def run_parser(sources=None, limit=20):
    """Background task to run the parser"""
    parser_status['is_running'] = True
    parser_status['last_run'] = datetime.now(timezone.utc)

    try:
        if sources:
            # Parse specific sources
            for source in sources:
                parser_status['current_section'] = f"{source}"
                print(f"[PARSER] Starting to parse: {source}", flush=True)
                orchestrator.parse_source(source, limit_per_section=limit)
                print(f"[PARSER] Completed parsing: {source}", flush=True)
        else:
            # Parse all sources
            parser_status['current_section'] = 'Все источники'
            print(f"[PARSER] Starting to parse all sources", flush=True)
            results = orchestrator.parse_all(limit_per_section=limit)
            print(f"[PARSER] Completed parsing all sources: {results}", flush=True)

        # AUTO AI ANALYSIS: Analyze all posts without AI analysis
        parser_status['current_section'] = 'AI анализ'
        print("[PARSER] Starting automatic AI analysis for new posts", flush=True)
        run_auto_ai_analysis()
        print("[PARSER] AI analysis completed", flush=True)

    except Exception as e:
        import traceback
        error_msg = f"Parser error: {e}\n{traceback.format_exc()}"
        print(error_msg, flush=True)
        parser_status['current_section'] = f"Ошибка: {str(e)}"

    finally:
        parser_status['is_running'] = False
        parser_status['current_section'] = None
        print("[PARSER] Parser stopped", flush=True)


@app.template_filter('time_ago')
def time_ago_filter(dt):
    """Template filter for time ago"""
    return time_ago(dt)


# Initialize application (runs on import, so works with gunicorn)
def init_app():
    """Initialize application components"""
    global automation_scheduler_enabled

    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('generated_reels', exist_ok=True)

    # Initialize database
    db.engine

    # Start parsing scheduler
    scheduler.start()

    print("=" * 50, flush=True)
    print("News Insight Parser - Version 2.0 + Automation", flush=True)
    print("=" * 50, flush=True)
    print("[OK] Universal architecture", flush=True)
    print("[OK] Multi-source support", flush=True)
    print("[OK] Signal prioritization", flush=True)
    print("[OK] Automatic scheduler", flush=True)
    print("[OK] AutoContentSystem", flush=True)
    print("=" * 50, flush=True)
    print(f"Registered sources: {', '.join(orchestrator.get_registered_sources())}", flush=True)
    print("=" * 50, flush=True)

    # Show parsing scheduler status
    sched_status = scheduler.get_status()
    if sched_status.get('auto_parse_enabled', False):
        enabled_sources = [name for name, data in sched_status.get('sources', {}).items()
                          if data.get('enabled', False)]
        print(f"[PARSER SCHEDULER] Auto-parse: ON | Sources: {', '.join(enabled_sources) if enabled_sources else 'none'}", flush=True)
    else:
        print("[PARSER SCHEDULER] Auto-parse: OFF", flush=True)

    # Start automation scheduler
    automation_scheduler.start()
    logger.info("Automation scheduler started")

    # Add automation job if enabled
    if AUTO_GENERATE_ENABLED and auto_system:
        try:
            automation_scheduler.add_job(
                func=scheduled_content_generation,
                trigger='cron',
                hour=AUTO_GENERATE_HOUR,
                minute=AUTO_GENERATE_MINUTE,
                id='daily_content_generation',
                name='Daily automated content generation',
                replace_existing=True
            )
            automation_scheduler_enabled = True
            logger.info(f"[AUTOMATION] Auto-generate: ON | Schedule: Daily at {AUTO_GENERATE_HOUR:02d}:{AUTO_GENERATE_MINUTE:02d}")
        except Exception as e:
            logger.error(f"Failed to schedule automation: {e}")
    else:
        logger.info("[AUTOMATION] Auto-generate: OFF (set AUTO_GENERATE_ENABLED=true to enable)")

    # Show automation status
    if auto_system:
        print(f"[AUTOMATION] Configured: YES | Telegram: {'YES' if telegram_poster else 'NO'}", flush=True)
    else:
        print("[AUTOMATION] Configured: NO (GROQ_API_KEY required)", flush=True)

    print("=" * 50, flush=True)

    # Register shutdown handler
    atexit.register(shutdown_scheduler)


def shutdown_scheduler():
    """Shutdown schedulers gracefully"""
    try:
        if scheduler:
            scheduler.shutdown()
            logger.info("Parser scheduler shutdown")
    except:
        pass

    try:
        if automation_scheduler:
            automation_scheduler.shutdown()
            logger.info("Automation scheduler shutdown")
    except:
        pass


# Initialize on module import (works with both gunicorn and direct run)
init_app()


if __name__ == '__main__':
    print("Starting server on http://localhost:5001", flush=True)
    print("=" * 50, flush=True)
    app.run(debug=True, host='0.0.0.0', port=5001)  # Use port 5001 to not conflict
