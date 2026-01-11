import time

_cache = {}

def get_cache(key):
    data = _cache.get(key)
    if not data:
        return None
    value, expiry = data
    if time.time() > expiry:
        _cache.pop(key, None)
        return None
    return value

def set_cache(key, value, ttl):
    _cache[key] = (value, time.time() + ttl)
