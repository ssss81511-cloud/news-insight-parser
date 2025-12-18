import requests

print('=== CHECKING VC BLOGS RSS FEEDS ===')
print()

# List of major VC blogs
vc_blogs = {
    'a16z': 'https://a16z.com/feed/',
    'YC': 'https://www.ycombinator.com/blog/feed',
    'Sequoia': 'https://www.sequoiacap.com/feed/',
    'First Round': 'https://review.firstround.com/feed',
    'NFX': 'https://www.nfx.com/rss',
}

headers = {'User-Agent': 'NewsInsightParser/2.0'}

for name, url in vc_blogs.items():
    try:
        r = requests.get(url, headers=headers, timeout=10)
        content_type = r.headers.get('Content-Type', 'unknown')
        
        print(f'{name:15} | Status: {r.status_code} | Type: {content_type[:30]}')
        
        if r.status_code == 200:
            # Check if RSS/XML
            if 'xml' in content_type.lower() or '<?xml' in r.text[:100]:
                print(f'               | ✓ RSS Available!')
            else:
                print(f'               | ✗ Not RSS (HTML page)')
        print()
        
    except Exception as e:
        print(f'{name:15} | Error: {str(e)[:50]}')
        print()
