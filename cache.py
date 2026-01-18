import time
import threading
from typing import Optional, Any, Union
from collections import OrderedDict
import weakref

class Cache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Thread-safe LRU cache with TTL support
        
        Args:
            max_size: Maximum number of items (default: 1000)
            default_ttl: Default TTL in seconds (default: 300 = 5min)
        """
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # Cleanup background thread
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Background thread to cleanup expired items"""
        while self._running:
            try:
                time.sleep(30)  # Check every 30 seconds
                self.cleanup()
            except Exception:
                pass
    
    def cleanup(self):
        """Remove all expired items"""
        with self._lock:
            now = time.time()
            to_remove = []
            
            for key in list(self._cache.keys()):
                value, expiry, _ = self._cache[key]
                if now > expiry:
                    to_remove.append(key)
            
            for key in to_remove:
                self._cache.pop(key, None)
            
            # LRU eviction if over max size
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry, access_time = self._cache[key]
            
            if time.time() > expiry:
                self._cache.pop(key, None)
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._cache[key] = (value, expiry, time.time())  # Update access time
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cache value with TTL"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (value, expiry, time.time())
            
            # LRU eviction if over max size
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
    
    def get_or_set(self, key: str, factory, ttl: Optional[int] = None) -> Any:
        """Get from cache or create with factory function"""
        value = self.get(key)
        if value is not None:
            return value
        
        value = factory()
        self.set(key, value, ttl)
        return value
    
    def delete(self, key: str):
        """Delete specific key"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
    
    def keys(self) -> list:
        """Get current cache keys"""
        with self._lock:
            return list(self._cache.keys())
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def stats(self) -> dict:
        """Get cache statistics"""
        with self._lock:
            now = time.time()
            active = sum(1 for _, (v, e, _) in self._cache.items() if now < e)
            return {
                'total': len(self._cache),
                'active': active,
                'expired': len(self._cache) - active,
                'max_size': self.max_size
            }
    
    def __del__(self):
        """Cleanup on destruction"""
        self._running = False

# 🔥 Global instance (backwards compatible)
_cache = Cache(max_size=1000, default_ttl=300)

# Backwards compatibility functions
def get_cache(key: str) -> Optional[Any]:
    return _cache.get(key)

def set_cache(key: str, value: Any, ttl: int):
    _cache.set(key, value, ttl)

def cleanup_cache():
    _cache.cleanup()

def clear_cache():
    _cache.clear()

# 🔹 Usage examples
if __name__ == "__main__":
    import asyncio
    
    # Sync usage
    set_cache("test", {"data": "hello"}, 10)
    print(get_cache("test"))  # Works
    
    # Async compatible (non-blocking)
    cache = Cache(max_size=100)
    
    def expensive_func():
        time.sleep(1)
        return "expensive result"
    
    result = cache.get_or_set("expensive", expensive_func, ttl=60)
    print(result)  # Cached after first call
    
    print(cache.stats())
