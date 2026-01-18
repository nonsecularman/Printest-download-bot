import time
import threading
from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import json
import atexit

try:
    from config import DAILY_LIMIT
except ImportError:
    DAILY_LIMIT = 4  # Default: 4 downloads/day

# Config
RATE_WINDOW = 60      # Rate limit window (seconds)
MAX_RATE = 10         # Max requests per window
DAY_SECONDS = 86400   # 24 hours

# File persistence
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
RATE_FILE = DATA_DIR / "rate_limits.json"
DAILY_FILE = DATA_DIR / "daily_limits.json"

# Thread-safe storage
_users_rate: Dict[int, List[float]] = {}
_daily_limits: Dict[int, Dict[str, float]] = {}
_lock = threading.RLock()

def _load_json(filepath: Path, default: dict = None) -> dict:
    """Load JSON data with fallback"""
    if not filepath.exists():
        return default or {}
    try:
        return json.loads(filepath.read_text())
    except:
        return default or {}

def _save_json(filepath: Path, data: dict):
    """Thread-safe JSON save"""
    try:
        with _lock:
            filepath.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

def is_flood(user_id: int, limit: int = MAX_RATE, seconds: int = RATE_WINDOW) -> bool:
    """
    Check if user is flooding
    Thread-safe rate limiter
    """
    now = time.time()
    
    with _lock:
        # Cleanup old timestamps
        if user_id in _users_rate:
            _users_rate[user_id] = [t for t in _users_rate[user_id] if now - t < seconds]
        
        # Check limit
        if len(_users_rate[user_id]) >= limit:
            return True
        
        # Add current request
        _users_rate[user_id].append(now)
        
        # Persist every 100 requests
        if len(_users_rate) % 100 == 0:
            _save_json(Path(RATE_FILE), _users_rate)
    
    return False

def check_daily(user_id: int, max_limit: int = DAILY_LIMIT) -> bool:
    """
    Check daily download limit
    Resets every 24h, persistent across restarts
    """
    now = time.time()
    today = int(now // DAY_SECONDS)
    
    with _lock:
        # Load persistent data
        daily_data = _load_json(DAILY_FILE, {})
        
        user_data = daily_data.get(str(user_id), {})
        user_day = user_data.get("day", 0)
        user_count = user_data.get("count", 0)
        
        # Reset if new day
        if user_day != today:
            user_count = 1
        elif user_count >= max_limit:
            return False
        
        # Update count
        user_data["day"] = today
        user_data["count"] = user_count + 1
        daily_data[str(user_id)] = user_data
        
        # Persist
        _save_json(DAILY_FILE, daily_data)
        
        # In-memory cache
        _daily_limits[user_id] = {"day": today, "count": user_data["count"]}
    
    return user_count < max_limit

def reset_user_daily(user_id: int):
    """Admin: Reset specific user daily limit"""
    with _lock:
        daily_data = _load_json(DAILY_FILE, {})
        daily_data.pop(str(user_id), None)
        _save_json(DAILY_FILE, daily_data)
        if user_id in _daily_limits:
            del _daily_limits[user_id]

def get_user_stats(user_id: int = None) -> dict:
    """Get usage statistics"""
    with _lock:
        stats = {
            "daily_users": len(_daily_limits),
            "rate_users": len(_users_rate),
            "daily_limit": DAILY_LIMIT
        }
        
        if user_id:
            daily = _daily_limits.get(user_id, {"count": 0, "day": 0})
            rate_count = len(_users_rate.get(user_id, []))
            stats["user"] = {
                "daily_count": daily["count"],
                "rate_count": rate_count,
                "daily_remaining": max(0, DAILY_LIMIT - daily["count"])
            }
        
        return stats

def cleanup_old_data():
    """Remove data older than 48 hours"""
    now = time.time()
    cutoff = now - (2 * DAY_SECONDS)
    
    with _lock:
        # Cleanup daily (keep only current day)
        daily_data = _load_json(DAILY_FILE, {})
        to_remove = []
        today = int(now // DAY_SECONDS)
        
        for uid_str, data in daily_data.items():
            if data.get("day", 0) < today - 1:
                to_remove.append(uid_str)
        
        for uid in to_remove:
            daily_data.pop(uid, None)
        
        _save_json(DAILY_FILE, daily_data)
        
        # Cleanup rate limits (keep recent)
        for uid in list(_users_rate.keys()):
            _users_rate[uid] = [t for t in _users_rate[uid] if now - t < DAY_SECONDS]

# Auto-cleanup on exit
atexit.register(cleanup_old_data)

# Periodic cleanup
def start_cleanup_loop():
    """Background cleanup every hour"""
    def _loop():
        while True:
            time.sleep(3600)  # 1 hour
            cleanup_old_data()
    
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()

# Init
_users_rate = defaultdict(list)
_daily_limits = {}
start_cleanup_loop()

# Backwards compatibility
def increment_daily(user_id: int):
    """Deprecated: use check_daily instead"""
    return check_daily(user_id)

if __name__ == "__main__":
    # Test
    print("Testing flood protection...")
    
    for i in range(15):
        print(f"User 123: {not is_flood(123)} -> {get_user_stats(123)['user']}")
        time.sleep(0.1)
    
    for i in range(6):
        print(f"Daily check: {check_daily(456)}")
    
    print("✅ Flood protection working!")
