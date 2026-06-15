import requests
from requests.auth import HTTPBasicAuth

site_url = 'https://litimez.ai'
username = 'Litimez'
app_password = '89Bo at0l cOzo wADL dH21 Drff'
api_url = f"{site_url}/wp-json/wp/v2"

session = requests.Session()
session.auth = HTTPBasicAuth(username, app_password)

# Test users/me
print("Test: users/me")
response = session.get(f"{api_url}/users/me", timeout=10)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"User: {response.json()['name']}")
else:
    print(f"Response: {response.text[:500]}")

# Test create post
print("\nTest: Create post")
data = {
    'title': 'Test from Worker',
    'content': 'Testing from worker container',
    'status': 'publish'
}
response = session.post(f"{api_url}/posts", json=data, timeout=30)
print(f"Status: {response.status_code}")
if response.status_code in [200, 201]:
    print(f"Post created: {response.json().get('link')}")
else:
    print(f"Response: {response.text[:500]}")
