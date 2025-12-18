"""
Test TechCrunch parser integration
"""
from parsers.techcrunch.parser import TechCrunchParser
from storage.universal_database import UniversalDatabaseManager
from loguru import logger

print('=== TESTING TECHCRUNCH PARSER ===')
print()

# Initialize parser
parser = TechCrunchParser()

# Test 1: Get available sections
print('Available sections:', parser.get_available_sections())
print()

# Test 2: Fetch posts from 'startups' category
print('Fetching posts from startups category...')
try:
    raw_posts = parser.fetch_posts('startups', limit=5)
    print(f'Fetched {len(raw_posts)} posts')

    if raw_posts:
        print()
        print('First post:')
        print(f"  Title: {raw_posts[0]['title'][:60]}...")
        print(f"  Author: {raw_posts[0].get('author', 'N/A')}")
        print(f"  Link: {raw_posts[0]['link'][:50]}...")
        print()

        # Test 3: Normalize post
        print('Normalizing post...')
        post = parser.normalize_post(raw_posts[0])

        if post:
            print(f'  Source: {post["source"]}')
            print(f'  Category: {post["category"]}')
            print(f'  Title: {post["title"][:50]}...')
            print(f'  Importance: {post["importance_score"]}')
            print(f'  Has focus themes: {post["metadata"].get("has_focus_themes", False)}')
            print()

            # Test 4: Save to database
            print('Testing database integration...')
            db = UniversalDatabaseManager('sqlite:///test_techcrunch.db')

            saved = parser.parse_and_save(db, 'startups', limit=3)
            print(f'Saved {saved} posts to database')
            print()

            # Check stats
            stats = db.get_stats()
            print(f'Total posts in DB: {stats.get("total_posts", 0)}')
            print()

            db.close()

            print('SUCCESS: TechCrunch parser working correctly!')
        else:
            print('ERROR: Failed to normalize post')
    else:
        print('No posts fetched')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
