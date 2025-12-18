import requests
import json

# Try common API patterns
endpoints = [
    'https://www.indiehackers.com/api/posts/recent',
    'https://www.indiehackers.com/api/posts/popular',
    'https://api.indiehackers.com/posts',
    'https://www.indiehackers.com/graphql',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

print('=== CHECKING INDIEHACKERS API ENDPOINTS ===')
print()

for endpoint in endpoints:
    try:
        r = requests.get(endpoint, headers=headers, timeout=10)
        print(f'Endpoint: {endpoint}')
        print(f'  Status: {r.status_code}')
        print(f'  Content-Type: {r.headers.get("Content-Type", "unknown")}')
        
        if r.status_code == 200:
            # Check if it's JSON
            try:
                data = r.json()
                print(f'  JSON: Yes! Keys: {list(data.keys())[:5]}')
            except:
                print(f'  JSON: No (HTML/Text)')
        print()
    except Exception as e:
        print(f'  Error: {e}')
        print()
