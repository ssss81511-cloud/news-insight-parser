"""
Flask web interface for News Insight Parser
"""
from flask import Flask, render_template, jsonify, request
from storage.database import DatabaseManager
from parsers.hacker_news.parser import HackerNewsParser
from utils.helpers import time_ago, truncate_text, clean_html
from datetime import datetime
import threading
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Initialize database
db = DatabaseManager()

# Global parser instance
hn_parser = HackerNewsParser(rate_limit_delay=1)

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

    return render_template('index.html',
                          stats=stats,
                          recent_runs=recent_runs,
                          parser_status=parser_status,
                          time_ago=time_ago)


@app.route('/posts')
def posts():
    """View all posts"""
    post_type = request.args.get('type', None)
    posts = db.get_recent_posts(limit=100, post_type=post_type)

    return render_template('posts.html',
                          posts=posts,
                          post_type=post_type,
                          time_ago=time_ago,
                          truncate_text=truncate_text,
                          clean_html=clean_html)


@app.route('/signals')
def signals():
    """View detected signals"""
    signals = db.get_recent_signals(limit=50)

    return render_template('signals.html',
                          signals=signals,
                          time_ago=time_ago)


@app.route('/api/parse', methods=['POST'])
def start_parsing():
    """Start parsing HN data"""
    if parser_status['is_running']:
        return jsonify({'status': 'error', 'message': 'Parser is already running'}), 400

    # Run parser in background thread
    thread = threading.Thread(target=run_parser)
    thread.start()

    return jsonify({'status': 'success', 'message': 'Parser started'})


@app.route('/api/status')
def get_status():
    """Get current parser status"""
    stats = db.get_stats()
    return jsonify({
        'parser_status': parser_status,
        'stats': stats
    })


def run_parser():
    """Background task to run the parser"""
    parser_status['is_running'] = True
    parser_status['last_run'] = datetime.utcnow()

    try:
        # Parse Ask HN
        parser_status['current_section'] = 'Ask HN'
        run_ask = db.start_parser_run('hacker_news', 'ask_hn')
        ask_posts = hn_parser.get_ask_hn(limit=20)

        items_count = 0
        for post_data in ask_posts:
            normalized = hn_parser.normalize_post(post_data)
            db_post = db.add_hn_post(normalized)

            # Get comments for this post
            comments = hn_parser.get_comments(post_data['id'], limit=10)
            for comment_data in comments:
                normalized_comment = hn_parser.normalize_comment(comment_data, db_post.id)
                db.add_hn_comment(normalized_comment)

            items_count += 1

        db.finish_parser_run(run_ask.id, items_count, 'success')

        # Parse Show HN
        parser_status['current_section'] = 'Show HN'
        run_show = db.start_parser_run('hacker_news', 'show_hn')
        show_posts = hn_parser.get_show_hn(limit=20)

        items_count = 0
        for post_data in show_posts:
            normalized = hn_parser.normalize_post(post_data)
            db_post = db.add_hn_post(normalized)

            # Get comments
            comments = hn_parser.get_comments(post_data['id'], limit=10)
            for comment_data in comments:
                normalized_comment = hn_parser.normalize_comment(comment_data, db_post.id)
                db.add_hn_comment(normalized_comment)

            items_count += 1

        db.finish_parser_run(run_show.id, items_count, 'success')

        # Parse New
        parser_status['current_section'] = 'New'
        run_new = db.start_parser_run('hacker_news', 'new')
        new_posts = hn_parser.get_new_stories(limit=20)

        items_count = 0
        for post_data in new_posts:
            normalized = hn_parser.normalize_post(post_data)
            db.add_hn_post(normalized)
            items_count += 1

        db.finish_parser_run(run_new.id, items_count, 'success')

    except Exception as e:
        print(f"Parser error: {e}")
        parser_status['current_section'] = f"Error: {str(e)}"

    finally:
        parser_status['is_running'] = False
        parser_status['current_section'] = None


@app.template_filter('time_ago')
def time_ago_filter(dt):
    """Template filter for time ago"""
    return time_ago(dt)


if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)

    # Initialize database
    db.engine

    print("=" * 50)
    print("News Insight Parser - Web Interface")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)
