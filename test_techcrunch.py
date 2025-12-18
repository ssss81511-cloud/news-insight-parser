import requests
import feedparser

print('=== CHECKING TECHCRUNCH RSS FEEDS ===')
print()

# TechCrunch RSS feeds to try
tc_feeds = {
    'Main': 'https://techcrunch.com/feed/',
    'Startups': 'https://techcrunch.com/category/startups/feed/',
    'Funding': 'https://techcrunch.com/category/venture/feed/',
    'Apps': 'https://techcrunch.com/category/apps/feed/',
}

headers = {'User-Agent': 'NewsInsightParser/2.0'}

for name, url in tc_feeds.items():
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f'{name:15} | Status: {r.status_code}')
        
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                print(f'{" "*15} | Articles: {len(feed.entries)}')
                print(f'{" "*15} | Latest: {feed.entries[0].title[:50]}...')
            else:
                print(f'{" "*15} | No entries found')
        print()
    except Exception as e:
        print(f'{name:15} | Error: {str(e)[:50]}')
        print()
