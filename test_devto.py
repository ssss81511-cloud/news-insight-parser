import requests
import json

print('=== DEV.TO API CHECK ===')
print()

# Test basic API call
r = requests.get('https://dev.to/api/articles?tag=startup&per_page=5', 
                 headers={'User-Agent': 'NewsInsightParser/2.0'}, 
                 timeout=10)

print(f'Status: {r.status_code}')
print(f'Content-Type: {r.headers.get("Content-Type")}')
print()

if r.status_code == 200:
    data = r.json()
    print(f'Articles received: {len(data)}')
    print()
    
    if data:
        print('First article:')
        a = data[0]
        print(f'  Title: {a["title"][:60]}...')
        print(f'  Author: {a["user"]["name"]}')
        print(f'  Tags: {a["tag_list"]}')
        print(f'  Reactions: {a["positive_reactions_count"]}')
        print(f'  Comments: {a["comments_count"]}')
        print(f'  Published: {a["published_at"]}')
        print(f'  URL: {a["url"]}')
        print()
        print('Available keys:', list(a.keys())[:10])
