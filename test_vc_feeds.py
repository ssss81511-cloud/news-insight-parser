import feedparser
import requests

print('=== TESTING YC BLOG FEED ===')
print()

r = requests.get('https://www.ycombinator.com/blog/feed', 
                 headers={'User-Agent': 'NewsInsightParser/2.0'})

feed = feedparser.parse(r.content)

print(f'Feed title: {feed.feed.title}')
print(f'Articles found: {len(feed.entries)}')
print()

if feed.entries:
    print('First 3 articles:')
    for i, entry in enumerate(feed.entries[:3]):
        print(f'\n{i+1}. {entry.title}')
        print(f'   Published: {entry.published if hasattr(entry, "published") else "N/A"}')
        print(f'   Link: {entry.link}')

print()
print('='*50)
print()
print('=== TESTING SEQUOIA BLOG FEED ===')
print()

r2 = requests.get('https://www.sequoiacap.com/feed/', 
                  headers={'User-Agent': 'NewsInsightParser/2.0'})

feed2 = feedparser.parse(r2.content)

print(f'Feed title: {feed2.feed.title}')
print(f'Articles found: {len(feed2.entries)}')
print()

if feed2.entries:
    print('First 3 articles:')
    for i, entry in enumerate(feed2.entries[:3]):
        print(f'\n{i+1}. {entry.title}')
        print(f'   Published: {entry.published if hasattr(entry, "published") else "N/A"}')
        print(f'   Link: {entry.link}')
