import httpx
import base64

url = 'https://litimez.ai/wp-json/wp/v2/users/me'
credentials = base64.b64encode(b'Litimez:89Bo at0l cOzo wADL dH21 Drff').decode()
headers = {'Authorization': f'Basic {credentials}'}

try:
    response = httpx.get(url, headers=headers, timeout=10.0, verify=True)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        print(f'User: {response.json()["name"]}')
    else:
        print(f'Response: {response.text[:500]}')
except Exception as e:
    print(f'Error: {e}')
