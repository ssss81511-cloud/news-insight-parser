import requests
from bs4 import BeautifulSoup

r = requests.get('https://www.indiehackers.com/posts', 
                 headers={'User-Agent': 'NewsInsightParser/2.0'}, 
                 timeout=10)

soup = BeautifulSoup(r.text, 'html.parser')

print('=== INDIEHACKERS PAGE STRUCTURE ===')
print()
print('Page title:', soup.title.string if soup.title else 'N/A')
print()

# Try different selectors
articles = soup.find_all('article', limit=5)
print(f'Found {len(articles)} article elements')

divs_with_post = soup.find_all('div', class_=lambda x: x and 'post' in x.lower(), limit=5)
print(f'Found {len(divs_with_post)} divs with "post" in class')

links = soup.find_all('a', href=lambda x: x and '/post/' in x, limit=5)
print(f'Found {len(links)} links with /post/ in href')
print()

if links:
    print('First 3 post links:')
    for i, link in enumerate(links[:3]):
        print(f'{i+1}. {link.get("href")}')
        print(f'   Text: {link.get_text().strip()[:60]}...')
