import os, requests, json

base = os.environ.get('PROMPT_TO_JSON_URL', 'http://127.0.0.1:8001')
username = os.environ.get('PROMPT_TO_JSON_USERNAME', 'admin')
password = os.environ.get('PROMPT_TO_JSON_PASSWORD', 'bhiv2024')

SPEC_IDS = ['spec_316fc275d309', 'spec_bc14ac4aac0c']

def trim(obj):
    if isinstance(obj, dict):
        return {k: (trim(v) if k not in ('spec_json','diff') else '<trimmed>') for k,v in obj.items()}
    if isinstance(obj, list):
        return [trim(i) for i in obj]
    return obj

print('Base URL:', base)
try:
    auth = requests.post(f"{base}/api/v1/auth/login", data={'username': username, 'password': password}, timeout=10)
    print('Auth status:', auth.status_code)
    auth.raise_for_status()
    token = auth.json().get('access_token')
    if not token:
        print('No token returned; auth response:', auth.text)
    else:
        headers = {'Authorization': f'Bearer {token}'}
        for sid in SPEC_IDS:
            print('\n=== Spec:', sid, '===')
            try:
                r = requests.get(f"{base}/api/v1/history/{sid}", headers=headers, params={'limit':10}, timeout=30)
                print('Status:', r.status_code)
                try:
                    data = r.json()
                    print(json.dumps(trim(data), indent=2)[:8000])
                except Exception as e:
                    print('Failed to parse JSON:', e, r.text[:2000])
            except Exception as e:
                print('Request error for', sid, e)
except Exception as e:
    print('Auth request error:', e)
