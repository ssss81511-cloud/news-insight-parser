import requests
import feedparser

print('=== CHECKING ALTERNATIVE VC BLOG URLS ===')
print()

# Alternative URLs to try
alternatives = {
    'a16z': [
        'https://a16z.com/rss',
        'https://future.com/feed/',  # a16z Future blog
    ],
    'First Round': [
        'https://firstround.com/review/feed',
        'https://firstround.com/feed',
    ],
}

headers = {'User-Agent': 'NewsInsightParser/2.0'}

for blog, urls in alternatives.items():
    print(f'Testing {blog}:')
    
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f'  {url}')
            print(f'    Status: {r.status_code}')
            
            if r.status_code == 200:
                # Try to parse as feed
                feed = feedparser.parse(r.content)
                if feed.entries:
                    print(f'    SUCCESS! Found {len(feed.entries)} articles')
                    print(f'    Title: {feed.entries[0].title[:50]}...')
                else:
                    print(f'    HTML page (not RSS)')
            print()
        except Exception as e:
            print(f'    Error: {str(e)[:40]}')
            print()
