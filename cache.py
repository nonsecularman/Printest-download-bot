# cache.py

_cache = {}

def get_cache(key, default=None):
    return _cache.get(key, default)

def set_cache(key, value):
    _cache[key] = value
