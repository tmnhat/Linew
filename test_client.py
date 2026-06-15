import sys
sys.path.insert(0, '/app')

from app.publisher.wordpress import get_wordpress_client

# Test WordPress client
client = get_wordpress_client()
print(f"Client username: {client.username}")
print(f"Client app_password: {client.app_password}")

# Test connection
result = client.test_connection()
print(f"Connection result: {result}")
