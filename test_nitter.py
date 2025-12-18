import requests
import feedparser

print('=== TESTING NITTER RSS ===')
print()

# Try to get RSS from Nitter
url = 'https://nitter.net/elonmusk/rss'

try:
    r = requests.get(url, headers={'User-Agent': 'NewsInsightParser/2.0'}, timeout=10)
    print(f'Status: {r.status_code}')
    print(f'Content preview (first 200 chars):')
    print(r.text[:200])
    print()
    
    # Try to parse as RSS
    feed = feedparser.parse(r.content)
    
    if feed.entries:
        print(f'SUCCESS! Found {len(feed.entries)} tweets')
        print()
        print('First tweet:')
        print(f'  Title: {feed.entries[0].title[:60]}...')
    else:
        print('Could not parse as RSS feed')
        
except Exception as e:
    print(f'Error: {e}')

print()
print('NOTE: Nitter is unstable and many instances are down')
print('Twitter/X requires paid API access since 2023')
