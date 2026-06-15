import requests
from requests.auth import HTTPBasicAuth

# Test với username từ settings
site_url = 'https://litimez.ai'
# Thử với username viết thường như config
username = 'Litimez'
app_password = '89Bo at0l cOzo wADL dH21 Drff'

print(f"Testing with username: '{username}'")

session = requests.Session()
session.auth = HTTPBasicAuth(username, app_password)
session.headers.update({
    "Content-Type": "application/json",
    "User-Agent": "Linew/1.0",
})

# Test users/me
response = session.get(f"{site_url}/wp-json/wp/v2/users/me", timeout=10)
print(f"users/me status: {response.status_code}")
if response.status_code == 200:
    print(f"User: {response.json()['name']}")
else:
    print(f"Response: {response.text[:300]}")

# Test create post
data = {
    'title': 'Test username capitalization',
    'content': 'Testing',
    'status': 'publish'
}
response = session.post(f"{site_url}/wp-json/wp/v2/posts", json=data, timeout=30)
print(f"\nCreate post status: {response.status_code}")
if response.status_code in [200, 201]:
    print(f"Post created: {response.json().get('link')}")
else:
    print(f"Response: {response.text[:300]}")
