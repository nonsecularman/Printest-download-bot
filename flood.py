"""
Flood Protection - FIXED for Heroku/Crashes
No more AttributeError or startup crashes
"""
import time
import threading
import json
import logging
import atexit
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

try:
    from config import DAILY_LIMIT
except ImportError:
    DAILY_LIMIT = 4

# Config
RATE_WINDOW = 60
MAX_RATE = 10
DAY_SECONDS = 86400
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flood")

# ✅ FIXED: Class-level storage 
class FloodProtector:
    _users_rate: Dict[int, List[float]] = defaultdict(list)
    _daily_limits: Dict[int, Dict] = {}
    _lock = threading.RLock()
    
    @staticmethod
    def _now() -> float:
        return time.time()
    
    @classmethod
    def is_flood(cls, user_id: int, limit: int = MAX_RATE, seconds: int = RATE_WINDOW) -> bool:
        now = cls._now()
        with cls._lock:
            # Clean expired
            cls._users_rate[user_id] = [
                t for t in cls._users_rate[user_id] if now - t < seconds
            ]
            
            if len(cls._users_rate[user_id]) >= limit:
                logger.warning(f"🚫 FLOOD: {user_id} ({len(cls._users_rate[user_id])}/{limit})")
                return True
            
            cls._users_rate[user_id].append(now)
            return False
    
    @classmethod
    def check_daily(cls, user_id: int, limit: int = DAILY_LIMIT) -> bool:
        now = cls._now()
        today = int(now // DAY_SECONDS)
        
        with cls._lock:
            daily_file = DATA_DIR / "daily_limits.json"
            daily_data = cls._load_json(daily_file)
            
            key = str(user_id)
            user_data = daily_data.get(key, {})
            user_day = user_data.get("day", 0)
            user_count = user_data.get("count", 0)
            
            if user_day != today:
                user_count = 1
            elif user_count >= limit:
                logger.warning(f"🚫 DAILY: {user_id} ({user_count}/{limit})")
                return False
            
            user_data.update({
                "day": today,
                "count": user_count + 1,
                "last_used": now
            })
            daily_data[key] = user_data
            cls._save_json(daily_file, daily_data)
            cls._daily_limits[user_id] = user_data
            
            logger.info(f"📈 {user_id}: {user_data['count']}/{limit}")
            return True
    
    @classmethod
    def get_stats(cls, user_id: Optional[int] = None) -> dict:
        with cls._lock:
            stats = {
                "daily_limit": DAILY_LIMIT,
                "daily_users": len(cls._daily_limits)
            }
            if user_id:
                daily = cls._daily_limits.get(user_id, {"count": 0})
                stats["user"] = {
                    "used": daily.get("count", 0),
                    "remaining": max(0, DAILY_LIMIT - daily.get("count", 0))
                }
            return stats
    
    @classmethod
    def reset_user(cls, user_id: int):
        with cls._lock:
            daily_file = DATA_DIR / "daily_limits.json"
            daily_data = cls._load_json(daily_file)
            daily_data.pop(str(user_id), None)
            cls._save_json(daily_file, daily_data)
            cls._users_rate[user_id].clear()
    
    @classmethod
    def _load_json(cls, filepath: Path) -> dict:
        if not filepath.exists():
            return {}
        try:
            return json.loads(filepath.read_text())
        except:
            return {}
    
    @classmethod
    def _save_json(cls, filepath: Path, data: dict):
        try:
            filepath.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

# ✅ FIXED: Safe cleanup - NO CRASH
def cleanup():
    try:
        logger.info("🧹 Flood cleanup")
    except:
        pass

atexit.register(cleanup)

# ✅ Auto-init on import (safe)
logger.info("✅ Flood protection LOADED")

# Backwards compatibility
is_flood = FloodProtector.is_flood
check_daily = FloodProtector.check_daily
get_stats = FloodProtector.get_stats
reset_user = FloodProtector.reset_user
