import requests

print('=== TESTING DEV.TO TAGS ===')
print()

tags = ['startup', 'entrepreneur', 'saas', 'buildinpublic', 'indiehacker']

for tag in tags:
    r = requests.get(f'https://dev.to/api/articles?tag={tag}&per_page=3',
                     headers={'User-Agent': 'NewsInsightParser/2.0'},
                     timeout=10)
    
    if r.status_code == 200:
        data = r.json()
        print(f'#{tag}: {len(data)} articles')
        if data:
            print(f'  Latest: "{data[0]["title"][:50]}..."')
    else:
        print(f'#{tag}: Error {r.status_code}')
    print()
