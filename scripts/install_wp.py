#!/usr/bin/env python3
"""Install WordPress automatically via REST API."""
import requests
from urllib.parse import urljoin

WP_URL = "https://litimez.ai"
BLOG_TITLE = "LiTimez"
ADMIN_USER = "admin"
ADMIN_EMAIL = "admin@litimez.ai"
ADMIN_PASS = "Linew2026!"  # Strong password

session = requests.Session()

# Step 1: Get install page
print("Step 1: Getting install page...")
resp = session.get(f"{WP_URL}/wp-admin/install.php")
resp.raise_for_status()
print(f"Status: {resp.status_code}")

# Step 2: Submit installation
print("\nStep 2: Submitting installation form...")
form_data = {
    "weblog_title": BLOG_TITLE,
    "user_name": ADMIN_USER,
    "admin_email": ADMIN_EMAIL,
    "admin_password": ADMIN_PASS,
    "admin_password2": ADMIN_PASS,
    "Submit": "Install+WordPress",
    "language": "en_US",
}

resp = session.post(
    f"{WP_URL}/wp-admin/install.php?step=2",
    data=form_data,
    allow_redirects=False
)
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")

if resp.status_code in (200, 302):
    print("✓ WordPress installation submitted!")
    if resp.status_code == 302:
        print(f"Redirect to: {resp.headers.get('Location', 'login page')}")
else:
    print(f"✗ Installation failed")
    print(resp.text[:500])

# Step 3: Login to verify
print("\nStep 3: Testing login...")
login_resp = session.post(
    f"{WP_URL}/wp-login.php",
    data={
        "log": ADMIN_USER,
        "pwd": ADMIN_PASS,
        "rememberme": "forever",
        "wp-submit": "Log+In",
        "redirect_to": f"{WP_URL}/wp-admin/",
        "testcookie": "1",
    },
    allow_redirects=False
)
print(f"Login status: {login_resp.status_code}")
if login_resp.status_code in (302, 200):
    print("✓ WordPress is installed and working!")
else:
    print("✗ Login failed")
