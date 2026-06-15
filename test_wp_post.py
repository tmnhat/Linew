import httpx
import base64
import json

# Test creating a post
url = 'https://litimez.ai/wp-json/wp/v2/posts'
credentials = base64.b64encode(b'Litimez:89Bo at0l cOzo wADL dH21 Drff').decode()
headers = {
    'Authorization': f'Basic {credentials}',
    'Content-Type': 'application/json'
}

data = {
    'title': 'Test Post from Container',
    'content': 'This is a test post created from Docker container',
    'status': 'publish'
}

try:
    response = httpx.post(url, headers=headers, json=data, timeout=30.0, verify=True)
    print(f'Status: {response.status_code}')
    if response.status_code in [200, 201]:
        result = response.json()
        print(f'Post created: {result.get("link", "No link")}')
        print(f'ID: {result.get("id")}')
    else:
        print(f'Response: {response.text[:1000]}')
except Exception as e:
    print(f'Error: {e}')
