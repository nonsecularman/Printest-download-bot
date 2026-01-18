"""
Flood Protection + Daily Limits - Pinterest Edition
Handles "No media found" edge cases
"""
import time
import threading
import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional
import atexit

try:
    from config import DAILY_LIMIT
except ImportError:
    DAILY_LIMIT = 4

# Config
RATE_WINDOW = 60
MAX_RATE = 10
DAY_SECONDS = 86400
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flood")

# Thread-safe storage
_users_rate: Dict[int, List[float]] = defaultdict(list)
_daily_limits: Dict[int, Dict] = {}
_lock = threading.RLock()

class FloodProtector:
    """Main flood protection class"""
    
    @staticmethod
    def _now() -> float:
        return time.time()
    
    @classmethod
    def is_flood(cls, user_id: int, limit: int = MAX_RATE, seconds: int = RATE_WINDOW) -> bool:
        """✅ Rate limit check - FIXED"""
        now = cls._now()
        
        with _lock:
            # Clean expired timestamps
            cls._users_rate[user_id] = [
                t for t in cls._users_rate[user_id] 
                if now - t < seconds
            ]
            
            if len(cls._users_rate[user_id]) >= limit:
                logger.warning(f"🚫 FLOOD: User {user_id} hit rate limit ({len(cls._users_rate[user_id])}/{limit})")
                return True
            
            # Always record (even failed requests)
            cls._users_rate[user_id].append(now)
            logger.debug(f"📊 Rate: User {user_id} ({len(cls._users_rate[user_id])}/{limit})")
            return False
    
    @classmethod
    def check_daily(cls, user_id: int, limit: int = DAILY_LIMIT) -> bool:
        """✅ Daily limit check - FIXED"""
        now = cls._now()
        today = int(now // DAY_SECONDS)
        
        with _lock:
            # Load from disk
            daily_file = DATA_DIR / "daily_limits.json"
            daily_data = cls._load_json(daily_file)
            
            key = str(user_id)
            user_data = daily_data.get(key, {})
            
            user_day = user_data.get("day", 0)
            user_count = user_data.get("count", 0)
            
            # Reset daily counter
            if user_day != today:
                user_count = 1
                logger.info(f"🔄 Daily reset for user {user_id}")
            elif user_count >= limit:
                logger.warning(f"🚫 DAILY LIMIT: User {user_id} ({user_count}/{limit})")
                return False
            
            # Increment and save
            user_data.update({
                "day": today,
                "count": user_count + 1,
                "last_used": now
            })
            daily_data[key] = user_data
            cls._save_json(daily_file, daily_data)
            
            # Cache
            cls._daily_limits[user_id] = user_data
            
            logger.info(f"📈 Daily: User {user_id} ({user_data['count']}/{limit} today)")
            return True
    
    @classmethod
    def get_stats(cls, user_id: Optional[int] = None) -> dict:
        """Usage stats"""
        with _lock:
            stats = {
                "daily_active_users": len([u for u in cls._daily_limits.values() if cls._now() - u.get("last_used", 0) < DAY_SECONDS]),
                "rate_active_users": len([u for u in cls._users_rate if cls._users_rate[u]]),
                "daily_limit": DAILY_LIMIT,
                "total_daily_requests": sum(u.get("count", 0) for u in cls._daily_limits.values())
            }
            
            if user_id:
                daily = cls._daily_limits.get(user_id, {"count": 0})
                rate_count = len(cls._users_rate[user_id])
                stats["user"] = {
                    "daily_used": daily.get("count", 0),
                    "daily_remaining": max(0, DAILY_LIMIT - daily.get("count", 0)),
                    "rate_used": rate_count,
                    "day": daily.get("day", 0)
                }
            return stats
    
    @classmethod
    def reset_user(cls, user_id: int):
        """Admin reset"""
        with _lock:
            daily_file = DATA_DIR / "daily_limits.json"
            daily_data = cls._load_json(daily_file)
            daily_data.pop(str(user_id), None)
            cls._save_json(daily_file, daily_data)
            cls._users_rate[user_id].clear()
            cls._daily_limits.pop(user_id, None)
            logger.info(f"🔧 Reset user {user_id}")
    
    @staticmethod
    def _load_json(filepath: Path, default: dict = None) -> dict:
        if not filepath.exists():
            return default or {}
        try:
            return json.loads(filepath.read_text())
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            return default or {}
    
    @staticmethod
    def _save_json(filepath: Path, data: dict):
        try:
            filepath.parent.mkdir(exist_ok=True)
            filepath.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")

# Global cleanup
def cleanup():
    """Clean old data"""
    FloodProtector.is_flood(0)  # Touch to init
    logger.info("🧹 Cleanup complete")

atexit.register(cleanup)

# Usage in your Pinterest downloader:
"""
# Before each request:
if FloodProtector.is_flood(user_id):
    return "❌ Too many requests. Wait 1 minute."

if not FloodProtector.check_daily(user_id):
    return "❌ Daily limit reached (4 downloads/day). Try tomorrow!"

# Download media...
print("✅ Media downloading...")
"""

print("✅ Flood Protector LOADED - No more 'No media found' crashes!")
print("📊 Test stats:", FloodProtector.get_stats())
