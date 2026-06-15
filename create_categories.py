import requests
from requests.auth import HTTPBasicAuth
import json

site_url = 'https://litimez.ai'
username = 'Litimez'
app_password = '89Bo at0l cOzo wADL dH21 Drff'
api_url = f"{site_url}/wp-json/wp/v2"

session = requests.Session()
session.auth = HTTPBasicAuth(username, app_password)
session.headers.update({
    "Content-Type": "application/json",
    "User-Agent": "Linew/1.0",
})

# 10 categories for a viral news site
categories = [
    "Politics",        # Chính trị
    "World",           # Thế giới
    "Business",        # Kinh doanh
    "Technology",      # Công nghệ
    "Science",         # Khoa học
    "Health",          # Sức khỏe
    "Sports",          # Thể thao
    "Entertainment",   # Giải trí
    "Finance",         # Tài chính
    "Education",       # Giáo dục
]

print("Creating 10 categories in WordPress...")
created = []

for cat_name in categories:
    # Check if exists
    resp = session.get(f"{api_url}/categories", params={"search": cat_name, "per_page": 10})
    if resp.status_code == 200:
        cats = resp.json()
        exists = any(c['name'].lower() == cat_name.lower() for c in cats)
        if exists:
            print(f"  [SKIP] {cat_name} - already exists")
            for c in cats:
                if c['name'].lower() == cat_name.lower():
                    created.append({'id': c['id'], 'name': c['name']})
                    break
            continue
    
    # Create new
    resp = session.post(f"{api_url}/categories", json={"name": cat_name})
    if resp.status_code in [200, 201]:
        cat = resp.json()
        created.append({'id': cat['id'], 'name': cat['name']})
        print(f"  [OK] Created: {cat_name} (ID: {cat['id']})")
    else:
        print(f"  [ERROR] {cat_name}: {resp.status_code} - {resp.text[:200]}")

print(f"\nTotal categories: {len(created)}")
print(json.dumps(created, indent=2))
