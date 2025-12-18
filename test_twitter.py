import requests

print('=== CHECKING TWITTER/X DATA ACCESS ===')
print()

# Try different approaches
approaches = {
    'Nitter RSS': 'https://nitter.net/elonmusk/rss',
    'Twitter API v2': 'https://api.twitter.com/2/tweets/search/recent',
}

headers = {'User-Agent': 'NewsInsightParser/2.0'}

for name, url in approaches.items():
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f'{name:20} | Status: {r.status_code}')
        print(f'{" "*20} | Type: {r.headers.get("Content-Type", "unknown")[:40]}')
        print()
    except Exception as e:
        print(f'{name:20} | Error: {str(e)[:60]}')
        print()

print('Note: Twitter API requires authentication')
print('Nitter instances may be down or rate-limited')
