import json
import os
import hashlib
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')

def _cache_path(key):
    h = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f'{h}.json')

def get(key, ttl_seconds=300):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if time.time() - data['ts'] > ttl_seconds:
            os.remove(path)
            return None
        return data['value']
    except Exception:
        return None

def set(key, value):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(key)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'ts': time.time(), 'value': value}, f, ensure_ascii=False)
